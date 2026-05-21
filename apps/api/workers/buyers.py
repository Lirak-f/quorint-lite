"""Worker 3 — Buyer discovery and receptiveness scoring via Apollo, PDL, Perplexity, 10times."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from langfuse import observe

from models import BuyerList, BuyerOutput, ManufacturerInput
from scoring.config_loader import load_sector_config
from scoring.engine import assign_tier, score_buyer

load_dotenv()

# Comtrade numeric codes for target EU countries
_ISO2_TO_COMTRADE = {
    "AT": "40", "DE": "276", "IT": "380", "FR": "251",
    "NL": "528", "BE": "56", "CH": "757", "PL": "616",
}

_COUNTRY_NAMES = {
    "AT": "Austria", "DE": "Germany", "IT": "Italy",
    "FR": "France", "NL": "Netherlands", "CH": "Switzerland",
    "BE": "Belgium", "PL": "Poland",
}


# ─────────────────────────────────────────
# Step 1: Apollo.io buyer discovery
# ─────────────────────────────────────────

def _apollo_search(
    target_iso2: str,
    person_titles: list[str],
    company_keywords: list[str],
    company_size_ranges: list[str],
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Search Apollo.io for buyers matching sector filters in the target country.
    Returns list of buyer dicts with contact details.
    """
    api_key = os.getenv("APOLLO_API_KEY")  # TODO: add APOLLO_API_KEY to .env
    if not api_key:
        print("[Apollo] No API key — skipping buyer discovery")
        return []

    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }

    payload = {
        "person_titles": person_titles[:5],  # Apollo caps title filters
        "prospected_by_current_team": "no",
        "person_locations": [_COUNTRY_NAMES.get(target_iso2, target_iso2)],
        "organization_locations": [_COUNTRY_NAMES.get(target_iso2, target_iso2)],
        "q_organization_keyword_tags": company_keywords[:8],
        "organization_num_employees_ranges": company_size_ranges,
        "page": 1,
        "per_page": min(limit, 50),
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 401:
            print("[Apollo] Invalid API key")
            return []
        if resp.status_code == 403:
            print("[Apollo] Endpoint not accessible on current plan — skipping (paid plan required for prospecting)")
            return []
        if resp.status_code == 422:
            print(f"[Apollo] Validation error: {resp.text[:200]}")
            return []
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        print(f"[Apollo] HTTP error: {e}")
        return []
    except Exception as e:
        print(f"[Apollo] Error: {e}")
        return []

    buyers = []
    for person in data.get("people", []):
        org = person.get("organization") or {}
        buyer = {
            "company_name": org.get("name", ""),
            "company_domain": org.get("website_url", ""),
            "city": person.get("city", ""),
            "country_iso2": target_iso2,
            "buyer_type": _infer_buyer_type(org.get("keywords", []), org.get("name", "")),
            "contact_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip() or None,
            "contact_title": person.get("title"),
            "contact_email": person.get("email"),
            "linkedin_url": person.get("linkedin_url"),
            "enrichment_source": "apollo",
            "revenue_trend": None,  # enriched later if possible
        }
        if buyer["company_name"]:
            buyers.append(buyer)

    return buyers


def _infer_buyer_type(keywords: list[str], company_name: str) -> Optional[str]:
    """Infer buyer type from company keywords and name."""
    text = " ".join(keywords).lower() + " " + company_name.lower()
    if any(w in text for w in ["wholesale", "großhandel", "grossiste", "ingrosso"]):
        return "wholesaler"
    if any(w in text for w in ["import", "distributor", "vertrieb"]):
        return "importer/distributor"
    if any(w in text for w in ["retail", "einzelhandel", "detaillant"]):
        return "retailer"
    if any(w in text for w in ["manufacturer", "hersteller", "produzent"]):
        return "manufacturer"
    return "buyer"


# ─────────────────────────────────────────
# Step 2: PDL enrichment
# ─────────────────────────────────────────

def _pdl_enrich(buyer: dict[str, Any]) -> dict[str, Any]:
    """
    Enrich a buyer record with PDL /v5/person/enrich.
    Only called when email or title is missing.
    """
    api_key = os.getenv("PDL_API_KEY")  # TODO: add PDL_API_KEY to .env
    if not api_key:
        return buyer

    domain = buyer.get("company_domain", "")
    name = buyer.get("contact_name", "")
    if not domain or not name:
        return buyer

    url = "https://api.peopledatalabs.com/v5/person/enrich"
    params = {
        "api_key": api_key,
        "company": domain,
        "name": name,
        "required": "emails",
        "pretty": "true",
    }

    try:
        resp = httpx.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            emails = data.get("data", {}).get("emails", [])
            if emails and not buyer.get("contact_email"):
                buyer["contact_email"] = emails[0].get("address")
                buyer["enrichment_source"] = "pdl"

            title = data.get("data", {}).get("job_title")
            if title and not buyer.get("contact_title"):
                buyer["contact_title"] = title
                buyer["enrichment_source"] = "pdl"
    except Exception as e:
        print(f"[PDL] Enrichment error for {name} at {domain}: {e}")

    return buyer


# ─────────────────────────────────────────
# Step 3: Comtrade mirror data
# ─────────────────────────────────────────

def _fetch_comtrade_mirror(hs_code: str, buyer_countries: list[str]) -> dict[str, Any]:
    """
    For each unique buyer country, fetch who imports the HS code and from which origins.
    Returns: {country_iso2: {origin_iso2: {value, trend}}}
    """
    hs6 = hs_code[:6].ljust(6, "0")
    mirror: dict[str, Any] = {}

    for country_iso2 in set(buyer_countries):
        reporter_code = _ISO2_TO_COMTRADE.get(country_iso2)
        if not reporter_code:
            continue

        url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
        params = {
            "reporterCode": reporter_code,
            "period": "2022,2023",
            "cmdCode": hs6,
            "flowCode": "M",
            "includeDesc": "true",
            "maxRecords": "500",
            "format": "JSON",
            "breakdownMode": "classic",
        }

        try:
            resp = httpx.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                mirror[country_iso2] = {}
                continue
            data = resp.json()
            records = data.get("data", [])

            # Build {partner_iso3: {value_2022, value_2023}} then compute trend
            partner_years: dict[str, dict[int, float]] = {}
            for r in records:
                partner_code = str(r.get("partnerCode", ""))
                if partner_code == "0":
                    continue
                partner_desc = r.get("partnerDesc", partner_code)
                year = int(r.get("period", 0))
                value = float(r.get("primaryValue", 0) or 0)
                if partner_desc not in partner_years:
                    partner_years[partner_desc] = {}
                partner_years[partner_desc][year] = value

            country_mirror: dict[str, Any] = {}
            for partner, years in partner_years.items():
                sorted_years = sorted(years.keys())
                v_end = years.get(sorted_years[-1], 0)
                v_start = years.get(sorted_years[0], 0) if len(sorted_years) > 1 else v_end
                trend = "growing" if v_end > v_start * 1.05 else "declining" if v_end < v_start * 0.95 else "stable"
                country_mirror[partner] = {"value": v_end, "trend": trend}

            mirror[country_iso2] = country_mirror
        except Exception as e:
            print(f"[Comtrade mirror] Error for {country_iso2}: {e}")
            mirror[country_iso2] = {}

    return mirror


# ─────────────────────────────────────────
# Step 4: Perplexity Sonar Pro — live signals
# ─────────────────────────────────────────

_PERPLEXITY_SIGNAL_PROMPT = (
    'Has {company_name} in {city}, {country} posted any procurement, purchasing, or sourcing '
    'job openings in the last 90 days? Any news about them expanding their supplier base or '
    'sourcing new products? Answer ONLY in JSON with no explanation: '
    '{{"job_posting": true/false, "sourcing_news": true/false, "summary": "one sentence"}}'
)


def _perplexity_buyer_signals(
    buyers: list[dict[str, Any]],
    target_iso2: str,
    max_buyers: int = 15,
) -> dict[str, Any]:
    """
    Query Perplexity Sonar Pro for live signals per buyer.
    Batches up to max_buyers to control cost. Returns {company_name: {job_posting, sourcing_news, summary}}.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        return {}  # no key — signals stay empty, scores degrade gracefully

    country_name = _COUNTRY_NAMES.get(target_iso2, target_iso2)
    signals: dict[str, Any] = {}

    for buyer in buyers[:max_buyers]:
        company = buyer.get("company_name", "")
        city = buyer.get("city", country_name)
        if not company:
            continue

        query = _PERPLEXITY_SIGNAL_PROMPT.format(
            company_name=company,
            city=city,
            country=country_name,
        )

        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a business intelligence analyst. "
                        "Answer ONLY with valid JSON — no markdown, no explanation. "
                        "Keys: job_posting (bool), sourcing_news (bool), summary (string)."
                    ),
                },
                {"role": "user", "content": query},
            ],
            "max_tokens": 200,
            "temperature": 0.0,
        }

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=25)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            # Parse JSON from response
            parsed = _parse_signal_json(content)
            signals[company] = parsed
        except Exception as e:
            if "401" not in str(e):
                print(f"[Perplexity signals] Error for {company}: {e}")
            signals[company] = {"job_posting": False, "sourcing_news": False, "summary": ""}

    return signals


def _parse_signal_json(content: str) -> dict[str, Any]:
    """Extract job_posting/sourcing_news JSON from Perplexity response."""
    default = {"job_posting": False, "sourcing_news": False, "summary": ""}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[^}]+\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return default


# ─────────────────────────────────────────
# Apollo fallback: Perplexity buyer discovery
# ─────────────────────────────────────────

_PERPLEXITY_DISCOVERY_PROMPT = (
    "List the top 10 furniture wholesalers, importers, and distributors in {country} "
    "that buy solid wood furniture (HS 9403) from European manufacturers. "
    "For each company provide: company name, city, website domain, and the name and title "
    "of their purchasing or procurement contact if known. "
    "Format your response as a JSON array: "
    '[{{"company_name": "", "city": "", "domain": "", "contact_name": "", "contact_title": ""}}]'
)

_DISCOVERY_PROMPT_BY_SECTOR = {
    "furniture_wood": (
        "List the top 10 furniture wholesalers, importers, and distributors in {country} "
        "that source solid wood furniture (dining tables, chairs, cabinets) from European manufacturers. "
        "For each: company name, city, website domain, purchasing contact name and title if known. "
        'JSON array only: [{{"company_name":"","city":"","domain":"","contact_name":"","contact_title":""}}]'
    ),
    "textiles_apparel": (
        "List the top 10 clothing wholesalers, importers, and buying agents in {country} "
        "that source apparel from European or Balkan manufacturers. "
        "For each: company name, city, domain, purchasing contact. "
        'JSON array only: [{{"company_name":"","city":"","domain":"","contact_name":"","contact_title":""}}]'
    ),
    "food_beverage": (
        "List the top 10 food importers, distributors, and specialty food wholesalers in {country} "
        "that import food products from European manufacturers. "
        "For each: company name, city, domain, purchasing contact. "
        'JSON array only: [{{"company_name":"","city":"","domain":"","contact_name":"","contact_title":""}}]'
    ),
}


def _perplexity_buyer_discovery(
    sector_name: str,
    target_iso2: str,
) -> list[dict[str, Any]]:
    """
    Use Perplexity Sonar Pro to discover buyers when Apollo returns no results.
    Returns list of buyer dicts (without enrichment_source set — caller sets it).
    """
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        print("[Perplexity discovery] No API key — trying Gemini fallback")
        return _gemini_buyer_discovery(sector_name, target_iso2)

    country_name = _COUNTRY_NAMES.get(target_iso2, target_iso2)
    prompt_template = _DISCOVERY_PROMPT_BY_SECTOR.get(sector_name, _PERPLEXITY_DISCOVERY_PROMPT)
    query = prompt_template.format(country=country_name)

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a B2B market research specialist. "
                    "Return ONLY a valid JSON array — no markdown, no explanation. "
                    "If you don't know a field, use an empty string."
                ),
            },
            {"role": "user", "content": query},
        ],
        "max_tokens": 1200,
        "temperature": 0.1,
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=40)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Perplexity discovery] API error: {e}")
        return []

    # Parse JSON array from response
    try:
        raw = json.loads(content)
        if isinstance(raw, list):
            companies = raw
        elif isinstance(raw, dict) and "companies" in raw:
            companies = raw["companies"]
        else:
            companies = []
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            try:
                companies = json.loads(match.group(0))
            except json.JSONDecodeError:
                print(f"[Perplexity discovery] Could not parse JSON from response")
                return []
        else:
            return []

    buyers = []
    for c in companies:
        if not c.get("company_name"):
            continue
        buyers.append({
            "company_name": c.get("company_name", ""),
            "company_domain": c.get("domain", ""),
            "city": c.get("city", ""),
            "country_iso2": target_iso2,
            "buyer_type": "buyer",
            "contact_name": c.get("contact_name") or None,
            "contact_title": c.get("contact_title") or None,
            "contact_email": None,
            "linkedin_url": None,
            "enrichment_source": "perplexity",
            "revenue_trend": None,
        })

    print(f"[Perplexity discovery] Found {len(buyers)} buyers in {country_name}")
    return buyers


def _gemini_buyer_discovery(
    sector_name: str,
    target_iso2: str,
) -> list[dict[str, Any]]:
    """Gemini fallback for buyer discovery when both Apollo and Perplexity are unavailable."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        print("[Gemini discovery] No API key — cannot discover buyers")
        return []

    country_name = _COUNTRY_NAMES.get(target_iso2, target_iso2)
    prompt_template = _DISCOVERY_PROMPT_BY_SECTOR.get(sector_name, _PERPLEXITY_DISCOVERY_PROMPT)
    query = prompt_template.format(country=country_name)

    gemini_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "company_name": {"type": "STRING"},
                "city": {"type": "STRING"},
                "domain": {"type": "STRING"},
                "contact_name": {"type": "STRING"},
                "contact_title": {"type": "STRING"},
            },
            "required": ["company_name", "city", "domain", "contact_name", "contact_title"],
        },
    }

    models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "generationConfig": {
            "maxOutputTokens": 1500,
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema,
        },
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = httpx.post(url, json=payload, timeout=40)
            if resp.status_code in (429, 404):
                continue
            resp.raise_for_status()
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            companies = json.loads(content) if isinstance(content, str) else content
            if not isinstance(companies, list):
                continue

            buyers = []
            for c in companies:
                if not c.get("company_name"):
                    continue
                buyers.append({
                    "company_name": c.get("company_name", ""),
                    "company_domain": c.get("domain", ""),
                    "city": c.get("city", ""),
                    "country_iso2": target_iso2,
                    "buyer_type": "buyer",
                    "contact_name": c.get("contact_name") or None,
                    "contact_title": c.get("contact_title") or None,
                    "contact_email": None,
                    "linkedin_url": None,
                    "enrichment_source": "perplexity",
                    "revenue_trend": None,
                })

            if buyers:
                print(f"[Gemini discovery] ({model}) found {len(buyers)} buyers in {country_name}")
                return buyers
        except Exception as e:
            print(f"[Gemini discovery {model} error: {e}]")
            continue

    return []


# ─────────────────────────────────────────
# Step 5: 10times API — trade fair exhibitors
# ─────────────────────────────────────────

def _fetch_trade_fair_exhibitors(
    sector: str,
    target_iso2: str,
    sector_fairs: list[dict],
) -> list[dict[str, Any]]:
    """
    Query 10times API for upcoming fairs. Cross-reference with sector YAML fair list.
    Returns enriched fair list with exhibitor names where available.
    """
    api_key = os.getenv("TENTIMES_API_KEY")  # TODO: add TENTIMES_API_KEY to .env

    # Use sector YAML fairs as the base; enrich with 10times if key available
    fairs = [dict(f) for f in sector_fairs]  # copy to avoid mutating YAML cache
    for fair in fairs:
        fair.setdefault("exhibitors", [])

    if not api_key:
        return fairs

    # Map sector names to 10times industry slugs
    industry_map = {
        "furniture_wood": "furniture",
        "textiles_apparel": "textiles",
        "food_beverage": "food",
        "auto_parts": "automotive",
        "metals_steel": "metals",
        "machinery": "machinery",
    }
    industry = industry_map.get(sector, sector)

    url = "https://api.10times.com/v1/events"
    params = {
        "token": api_key,
        "industry": industry,
        "country": target_iso2,
        "size": 10,
    }

    try:
        resp = httpx.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            return fairs
        data = resp.json()
        events = data.get("data", data.get("events", []))

        # Merge 10times results into YAML fair list by name fuzzy match
        for event in events:
            event_name = event.get("event_name", event.get("name", ""))
            exhibitors = [
                e.get("company_name", e.get("name", ""))
                for e in event.get("exhibitors", [])
                if e.get("company_name") or e.get("name")
            ]

            matched = False
            for fair in fairs:
                if event_name.lower() in fair["name"].lower() or fair["name"].lower() in event_name.lower():
                    fair["exhibitors"].extend(exhibitors)
                    matched = True
                    break

            if not matched and exhibitors:
                fairs.append({
                    "name": event_name,
                    "country": target_iso2,
                    "exhibitors": exhibitors,
                })
    except Exception as e:
        print(f"[10times] Error: {e}")

    return fairs


# ─────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────

@observe(name="worker_buyers")
def run_buyers(
    hs_code: str,
    origin_iso2: str,
    target_iso2: str,
    manufacturer: ManufacturerInput,
) -> BuyerList:
    """
    Full Worker 3 pipeline: Apollo discovery → PDL enrichment → Comtrade mirror →
    Perplexity signals → 10times fairs → receptiveness scoring.
    Returns BuyerList with warm (≥70) and cold (40–69) tiers.

    Canonical test: hs_code="940360", origin="XK", target="AT"
    """
    sector = load_sector_config(hs_code)
    buyer_filters = sector.get("buyer_filters", {})
    sector_fairs = sector.get("trade_fairs", [])
    sector_name = sector.get("sector_name", "")

    # Step 1: Apollo discovery → Perplexity fallback if Apollo returns nothing
    raw_buyers = _apollo_search(
        target_iso2=target_iso2,
        person_titles=buyer_filters.get("person_titles", []),
        company_keywords=buyer_filters.get("company_keywords", []),
        company_size_ranges=buyer_filters.get("company_size_ranges", ["11-50", "51-200"]),
        limit=50,
    )
    if not raw_buyers:
        print("[Worker 3] Apollo returned no buyers — falling back to Perplexity discovery")
        raw_buyers = _perplexity_buyer_discovery(sector_name, target_iso2)

    # Step 2: PDL enrichment for records missing email or title
    enriched_buyers = []
    for buyer in raw_buyers:
        if not buyer.get("contact_email") or not buyer.get("contact_title"):
            buyer = _pdl_enrich(buyer)
        enriched_buyers.append(buyer)

    # Step 3: Comtrade mirror — import pattern per unique buyer country
    buyer_countries = list({b.get("country_iso2", target_iso2) for b in enriched_buyers})
    comtrade_mirror = _fetch_comtrade_mirror(hs_code, buyer_countries)

    # Step 4: Perplexity signals (max 15 buyers to control cost)
    perplexity_signals = _perplexity_buyer_signals(enriched_buyers, target_iso2, max_buyers=15)

    # Step 5: 10times trade fair exhibitor cross-reference
    trade_fairs = _fetch_trade_fair_exhibitors(sector_name, target_iso2, sector_fairs)

    # Step 6: Score each buyer
    scored: list[tuple[int, list[str], dict]] = []
    for buyer in enriched_buyers:
        s, signals = score_buyer(
            buyer=buyer,
            manufacturer=manufacturer,
            comtrade_mirror=comtrade_mirror,
            perplexity_signals=perplexity_signals,
            trade_fairs=trade_fairs,
        )
        tier = assign_tier(s)
        scored.append((s, signals, buyer, tier))

    # Step 7: Sort descending by score, keep warm top-5 and cold next-10
    scored.sort(key=lambda x: x[0], reverse=True)

    warm: list[BuyerOutput] = []
    cold: list[BuyerOutput] = []

    for s, signals, buyer, tier in scored:
        if tier == "skip":
            continue

        enrichment_src = buyer.get("enrichment_source", "apollo")
        # Validate enrichment_source is one of the allowed literals
        if enrichment_src not in ("apollo", "pdl", "perplexity"):
            enrichment_src = "apollo"

        buyer_out = BuyerOutput(
            company_name=buyer.get("company_name", ""),
            company_domain=buyer.get("company_domain"),
            city=buyer.get("city"),
            country_iso2=buyer.get("country_iso2", target_iso2),
            buyer_type=buyer.get("buyer_type"),
            contact_name=buyer.get("contact_name"),
            contact_title=buyer.get("contact_title"),
            contact_email=buyer.get("contact_email"),
            linkedin_url=buyer.get("linkedin_url"),
            enrichment_source=enrichment_src,
            receptiveness_score=s,
            receptiveness_signals=signals,
            tier=tier,
        )

        if tier == "warm" and len(warm) < 5:
            warm.append(buyer_out)
        elif tier == "cold" and len(cold) < 10:
            cold.append(buyer_out)

        if len(warm) >= 5 and len(cold) >= 10:
            break

    total_scored = len([x for x in scored if x[3] != "skip"])

    return BuyerList(
        warm=warm,
        cold=cold,
        total_scored=total_scored,
    )
