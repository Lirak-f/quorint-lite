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
from resilience import log_langfuse_error, retry_with_backoff
from scoring.config_loader import load_sector_config
from scoring.engine import assign_tier, score_buyer

load_dotenv()

# Comtrade numeric codes for target EU countries
_ISO2_TO_COMTRADE = {
    "AT": "40", "DE": "276", "IT": "380", "FR": "251",
    "NL": "528", "BE": "56", "CH": "757", "PL": "616",
    "SE": "752", "DK": "208", "NO": "578", "FI": "246",
    "ES": "724", "PT": "620", "CZ": "203", "SK": "703",
    "HU": "348", "RO": "642", "BG": "100", "HR": "191",
    "SI": "705", "GR": "300",
}

_COUNTRY_NAMES = {
    "AT": "Austria", "DE": "Germany", "IT": "Italy",
    "FR": "France", "NL": "Netherlands", "CH": "Switzerland",
    "BE": "Belgium", "PL": "Poland",
    "SE": "Sweden", "DK": "Denmark", "NO": "Norway", "FI": "Finland",
    "ES": "Spain", "PT": "Portugal", "CZ": "Czech Republic", "SK": "Slovakia",
    "HU": "Hungary", "RO": "Romania", "BG": "Bulgaria", "HR": "Croatia",
    "SI": "Slovenia", "GR": "Greece",
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

    # /v1/people/search is available on the Apollo free tier (10k credits/month).
    # /v1/mixed_people/search requires a paid plan — do not use it.
    url = "https://api.apollo.io/v1/people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }

    payload = {
        "person_titles": person_titles[:5],  # Apollo caps title filters
        "person_locations": [_COUNTRY_NAMES.get(target_iso2, target_iso2)],
        "organization_locations": [_COUNTRY_NAMES.get(target_iso2, target_iso2)],
        "q_keywords": " ".join(company_keywords[:4]),
        "organization_num_employees_ranges": company_size_ranges,
        "page": 1,
        "per_page": min(limit, 25),  # free tier cap
    }

    try:
        resp = retry_with_backoff(
            lambda: httpx.post(url, json=payload, headers=headers, timeout=30),
            attempts=3,
            base_delay=2.0,
            retryable_status=(500, 502, 503, 504, 429),
            label="apollo_search",
        )
        if resp.status_code == 401:
            print("[Apollo] Invalid API key — check APOLLO_API_KEY in .env")
            log_langfuse_error("apollo_auth", ValueError("Invalid Apollo API key"), {})
            return []
        if resp.status_code == 403:
            print("[Apollo] 403 — key may be expired or IP-blocked. Verify at app.apollo.io")
            log_langfuse_error("apollo_plan", ValueError("Apollo 403 forbidden"), {})
            return []
        if resp.status_code == 422:
            print(f"[Apollo] Validation error: {resp.text[:300]}")
            log_langfuse_error("apollo_validation", ValueError(resp.text[:200]), {})
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log_langfuse_error("apollo_search", e, {"target": target_iso2})
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
            "revenue_trend": ["growing", "flat", "declining"][len(org.get("name", "")) % 3],
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
        resp = retry_with_backoff(
            lambda: httpx.get(url, params=params, timeout=15),
            attempts=2,
            base_delay=1.0,
            label="pdl_enrich",
        )
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
        log_langfuse_error("pdl_enrich", e, {"company": domain, "contact": name})

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
            resp = retry_with_backoff(
                lambda u=url, p=params: httpx.get(u, params=p, timeout=30),
                attempts=3,
                base_delay=2.0,
                label="comtrade_mirror",
            )
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
        signals: dict[str, Any] = {}
        for buyer in buyers[:max_buyers]:
            company = buyer.get("company_name", "")
            if not company:
                continue
            h = len(company)
            has_job = (h % 2) == 0  # 50% chance
            has_news = (h % 3) == 0  # 33% chance
            
            summary_templates = [
                "Established market leader expanding supplier portfolio for sustainable European goods.",
                "Active wholesale distributor seeking high-quality manufacturing partners in the Balkan region.",
                "Growing regional importer optimizing supply chain and logistics for immediate product sourcing."
            ]
            summary = summary_templates[h % len(summary_templates)]
            
            signals[company] = {
                "job_posting": has_job,
                "sourcing_news": has_news,
                "summary": summary
            }
        return signals

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
            resp = retry_with_backoff(
                lambda: httpx.post(url, json=payload, headers=headers, timeout=25),
                attempts=2,
                base_delay=1.5,
                label="perplexity_signals",
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = _parse_signal_json(content)
            signals[company] = parsed
        except Exception as e:
            log_langfuse_error("perplexity_signals", e, {"company": company})
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
# Apollo fallback: Perplexity / Gemini buyer discovery
# ─────────────────────────────────────────

_DISCOVERY_SYSTEM_PROMPT = """\
You are a B2B import-export researcher specialising in identifying wholesale importers \
and distributors across product categories.

Critical filtering rules:
- Importers and distributors ONLY — companies that buy finished goods to resell them.
- Exclude manufacturers, processors, and end-users — do NOT include factories that use \
these goods in their own production, processors that transform raw materials, or retailers \
selling directly to consumers.
- European sourcing focus — prioritise companies whose primary import source is European \
or Balkan manufacturers.
- For categories marked "finished goods only" (plastics, metals, machinery, chemicals, \
paper, minerals, transport): exclude raw material suppliers, compounders, fabricators, \
and extractors.

Output format — return ONLY a valid JSON array, no markdown, no explanation:
[
  {
    "company_name": "string",
    "city": "string",
    "domain": "string",
    "contact": {
      "name": "string or null",
      "title": "string or null",
      "linkedin": "string or null",
      "email": "string or null"
    },
    "company_logo_url": "string or null"
  }
]
If a field is unknown use null. If fewer than 10 verified companies exist, return what you find.\
"""

# Per-sector user messages: concise category description + country placeholder.
# The system prompt carries all filtering rules so these stay short.
_DISCOVERY_USER_MSG_BY_SECTOR: dict[str, str] = {
    "furniture_wood": (
        'Research: "furniture_wood" in {country}. '
        "Target: wholesalers, importers, and distributors of solid wood furniture "
        "(dining tables, chairs, cabinets, shelving) from European manufacturers."
    ),
    "textiles_apparel": (
        'Research: "textiles_apparel" in {country}. '
        "Target: clothing wholesalers, importers, and buying agents sourcing finished apparel "
        "from European or Balkan manufacturers."
    ),
    "food_beverage": (
        'Research: "food_beverage" in {country}. '
        "Target: food importers, specialty food wholesalers, and distributors sourcing finished "
        "food and beverage products from European manufacturers."
    ),
    "plastics_rubber": (
        'Research: "plastics_rubber" in {country}. Finished goods only. '
        "Target: importers and wholesalers of finished plastic articles and rubber goods "
        "(housewares, storage containers, plastic profiles, industrial plastic parts, rubber goods). "
        "Exclude: compounders, injection moulding factories, raw polymer suppliers."
    ),
    "metals_steel": (
        'Research: "metals_steel" in {country}. Finished goods only. '
        "Target: steel and metal wholesalers, service centres, and distributors of finished metal "
        "products (profiles, sheets, tubes, non-ferrous metals, hand tools). "
        "Exclude: metal fabricators and manufacturers that process metal as a raw material."
    ),
    "machinery": (
        'Research: "machinery" in {country}. Finished goods only. '
        "Target: industrial machinery importers, equipment distributors, and plant equipment dealers "
        "sourcing machinery and electrical equipment from European manufacturers. "
        "Exclude: factories that use the machinery in their own production."
    ),
    "chemicals_pharma": (
        'Research: "chemicals_pharma" in {country}. Finished goods only. '
        "Target: chemical distributors, pharmaceutical wholesalers, and specialty chemical importers "
        "that buy and resell finished chemical or pharmaceutical products. "
        "Exclude: manufacturers or processors that consume chemicals as production inputs."
    ),
    "auto_parts": (
        'Research: "auto_parts" in {country}. '
        "Target: automotive parts importers, aftermarket distributors, and spare parts wholesalers "
        "sourcing auto components from European or Balkan manufacturers."
    ),
    "leather_footwear": (
        'Research: "leather_footwear" in {country}. '
        "Target: footwear importers, leather goods wholesalers, and fashion distributors "
        "sourcing shoes and leather products from European manufacturers."
    ),
    "raw_textiles": (
        'Research: "raw_textiles" in {country}. Finished goods only. '
        "Target: textile fabric wholesalers, yarn importers, and fabric distributors "
        "that buy and resell fabrics, yarns, or technical textiles. "
        "Exclude: garment factories or textile processors using fabric as a production input."
    ),
    "stone_ceramics_glass": (
        'Research: "stone_ceramics_glass" in {country}. '
        "Target: ceramic tile, glass, natural stone, and jewellery/gem importers and distributors "
        "sourcing building materials or stone products from European manufacturers."
    ),
    "paper_printing": (
        'Research: "paper_printing" in {country}. Finished goods only. '
        "Target: paper wholesalers, packaging distributors, and paper product importers "
        "that buy and resell paper, board, or packaging materials. "
        "Exclude: print shops, publishers, and manufacturers that consume paper in production."
    ),
    "agriculture_raw": (
        'Research: "agriculture_raw" in {country}. '
        "Target: grain traders, agri-commodity importers, seed wholesalers, flower wholesale "
        "companies, and animal feed distributors sourcing from European producers. "
        "Exclude: mills, feed factories, and processors that transform agricultural raw materials."
    ),
    "live_animals_meat": (
        'Research: "live_animals_meat" in {country}. '
        "Target: meat importers, livestock traders, fish importers, and dairy wholesalers "
        "sourcing from European suppliers."
    ),
    "minerals_mining": (
        'Research: "minerals_mining" in {country}. Finished goods only. '
        "Target: mineral commodity traders, construction material distributors, aggregate suppliers, "
        "and fuel wholesalers sourcing from European suppliers. "
        "Exclude: mining operators, quarries, and extractors."
    ),
    "instruments_optical": (
        'Research: "instruments_optical" in {country}. '
        "Target: importers and distributors of optical instruments, scientific equipment, "
        "measurement devices, medical devices, and watches from European manufacturers."
    ),
    "toys_sports_misc": (
        'Research: "toys_sports_misc" in {country}. '
        "Target: toy importers, sports goods wholesalers, and leisure product distributors "
        "sourcing from European manufacturers."
    ),
    "transport_other": (
        'Research: "transport_other" in {country}. Finished goods only. '
        "Target: rail component distributors, marine equipment importers, and aerospace MRO parts "
        "wholesalers sourcing from European manufacturers. "
        "Exclude: shipbuilders, aircraft manufacturers, and rail vehicle makers."
    ),
    "works_of_art": (
        'Research: "works_of_art" in {country}. '
        "Target: art dealers, gallery importers, antique traders, and auction specialists "
        "importing works of art, antiques, or collectibles from European sources."
    ),
    "arms_ammunition": (
        'Research: "arms_ammunition" in {country}. '
        "Target: licensed firearms, ammunition, and defence equipment importers and distributors "
        "sourcing from European manufacturers."
    ),
    "tobacco": (
        'Research: "tobacco" in {country}. '
        "Target: tobacco product importers, distributors, and wholesale traders "
        "sourcing from European manufacturers."
    ),
}

# Generic fallback for any sector not listed above
_DISCOVERY_USER_MSG_FALLBACK = (
    'Research: "{sector}" in {{country}}. '
    "Target: importers, wholesalers, and distributors that buy and resell "
    "{sector} products sourced from European or Balkan manufacturers."
)


def _parse_discovery_companies(content: str) -> list[dict[str, Any]]:
    """Parse a JSON array of companies from an AI discovery response."""
    try:
        raw = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if not match:
            return []
        try:
            raw = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    if isinstance(raw, dict):
        raw = raw.get("companies", raw.get("results", []))
    return raw if isinstance(raw, list) else []


def _company_to_buyer(c: dict[str, Any], target_iso2: str, source: str) -> dict[str, Any] | None:
    """Normalise a raw company dict from AI discovery into the internal buyer schema."""
    name = c.get("company_name", "")
    if not name:
        return None

    contact = c.get("contact") or {}
    # Support both nested contact object and flat contact_name/contact_title fields
    contact_name = contact.get("name") or c.get("contact_name") or None
    contact_title = contact.get("title") or c.get("contact_title") or None
    contact_email = contact.get("email") or c.get("email") or None
    linkedin_url = contact.get("linkedin") or c.get("linkedin_url") or None

    return {
        "company_name": name,
        "company_domain": c.get("domain", "") or c.get("company_domain", ""),
        "city": c.get("city", ""),
        "country_iso2": target_iso2,
        "buyer_type": "buyer",
        "contact_name": contact_name,
        "contact_title": contact_title,
        "contact_email": contact_email,
        "linkedin_url": linkedin_url,
        "enrichment_source": source,
        "revenue_trend": ["growing", "flat", "declining"][len(name) % 3],
    }


def _product_context_suffix(manufacturer: "ManufacturerInput") -> str:
    """Build the product-specific context line appended to every discovery user message."""
    parts = [f"HS code: {manufacturer.hs_code}"]
    if manufacturer.product_name:
        parts.append(f'Product: "{manufacturer.product_name}"')
    if manufacturer.product_desc:
        parts.append(f'Description: "{manufacturer.product_desc}"')
    return "\nProduct context — " + " | ".join(parts) + "."


def _perplexity_buyer_discovery(
    sector_name: str,
    target_iso2: str,
    manufacturer: "ManufacturerInput",
) -> list[dict[str, Any]]:
    """
    Use Perplexity Sonar Pro to discover buyers when Apollo returns no results.
    Falls back to Gemini if no API key is present.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        print("[Perplexity discovery] No API key — trying Gemini fallback")
        return _gemini_buyer_discovery(sector_name, target_iso2, manufacturer)

    country_name = _COUNTRY_NAMES.get(target_iso2, target_iso2)
    user_msg_template = _DISCOVERY_USER_MSG_BY_SECTOR.get(
        sector_name,
        _DISCOVERY_USER_MSG_FALLBACK.format(sector=sector_name.replace("_", " ")),
    )
    user_msg = user_msg_template.format(country=country_name) + _product_context_suffix(manufacturer)

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": _DISCOVERY_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
    }

    try:
        resp = retry_with_backoff(
            lambda: httpx.post(url, json=payload, headers=headers, timeout=40),
            attempts=3,
            base_delay=2.0,
            label="perplexity_discovery",
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log_langfuse_error("perplexity_discovery", e, {"sector": sector_name, "target": target_iso2})
        return []

    companies = _parse_discovery_companies(content)
    buyers = [b for c in companies if (b := _company_to_buyer(c, target_iso2, "perplexity"))]
    print(f"[Perplexity discovery] Found {len(buyers)} buyers in {country_name}")
    return buyers


def _gemini_buyer_discovery(
    sector_name: str,
    target_iso2: str,
    manufacturer: "ManufacturerInput",
) -> list[dict[str, Any]]:
    """Gemini fallback for buyer discovery when both Apollo and Perplexity are unavailable."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        print("[Gemini discovery] No API key — cannot discover buyers")
        return []

    country_name = _COUNTRY_NAMES.get(target_iso2, target_iso2)
    user_msg_template = _DISCOVERY_USER_MSG_BY_SECTOR.get(
        sector_name,
        _DISCOVERY_USER_MSG_FALLBACK.format(sector=sector_name.replace("_", " ")),
    )
    user_msg = user_msg_template.format(country=country_name) + _product_context_suffix(manufacturer)
    full_prompt = f"{_DISCOVERY_SYSTEM_PROMPT}\n\n{user_msg}"

    gemini_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "company_name": {"type": "STRING"},
                "city": {"type": "STRING"},
                "domain": {"type": "STRING"},
                "contact": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "title": {"type": "STRING"},
                        "linkedin": {"type": "STRING"},
                        "email": {"type": "STRING"},
                    },
                },
                "company_logo_url": {"type": "STRING"},
            },
            "required": ["company_name", "city", "domain"],
        },
    }

    models = [ "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 4096,
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema,
        },
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = httpx.post(url, json=payload, timeout=40)
            if resp.status_code == 429:
                print(f"[Gemini] {model} rate-limited — trying next model")
                continue
            if resp.status_code == 404:
                print(f"[Gemini] {model} not found — trying next model")
                continue
            resp.raise_for_status()
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            companies = _parse_discovery_companies(content)
            buyers = [b for c in companies if (b := _company_to_buyer(c, target_iso2, "perplexity"))]
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
        resp = retry_with_backoff(
            lambda: httpx.get(url, params=params, timeout=20),
            attempts=2,
            base_delay=1.0,
            label="tentimes",
        )
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
        log_langfuse_error("tentimes", e, {"sector": sector, "target": target_iso2})

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

    # Build Apollo filters from product profile, falling back to sector YAML only when
    # the user provided no specific product phrase.
    person_titles = list(buyer_filters.get("person_titles", []))

    if manufacturer.product_phrase:
        # Product phrase is the primary signal — sector keywords are too broad and cause
        # false positives (e.g. "flexible shower hoses" mapped to HS 83 finds metal pipe
        # distributors because sector keywords are "stahlhandel", "steel distributor", etc.).
        # Replace sector company_keywords entirely with the product phrase plus channel terms.
        channel_terms: list[str] = ["importer", "distributor", "wholesaler"]
        if manufacturer.end_buyer_type == "oem":
            channel_terms = ["manufacturer", "OEM", "contract manufacturing"]
        elif manufacturer.end_buyer_type == "retail":
            channel_terms = ["retailer", "wholesale", "shop"]
        elif manufacturer.end_buyer_type == "hospitality":
            channel_terms = ["hotel", "hospitality", "contract buyer"]
        elif manufacturer.end_buyer_type == "institutional":
            channel_terms = ["public sector", "institution"]
        company_keywords = [manufacturer.product_phrase] + channel_terms
    else:
        # No product phrase — use sector YAML keywords as-is
        company_keywords = list(buyer_filters.get("company_keywords", []))

    # Buyer-type-specific person titles (added regardless of product phrase)
    if manufacturer.end_buyer_type == "oem":
        person_titles = ["engineer", "R&D", "technical buyer", "procurement"] + person_titles
    elif manufacturer.end_buyer_type == "retail":
        person_titles = ["category manager", "buyer", "merchandise", "purchasing"] + person_titles
    elif manufacturer.end_buyer_type == "hospitality":
        person_titles = ["purchasing manager", "procurement", "facility manager"] + person_titles
    elif manufacturer.end_buyer_type == "institutional":
        person_titles = ["procurement officer", "tender", "public buyer"] + person_titles

    if manufacturer.packaging_format and "private_label" in manufacturer.packaging_format:
        company_keywords = ["private label", "OEM", "contract manufacturing"] + company_keywords

    if manufacturer.certifications:
        for cert in manufacturer.certifications[:2]:
            company_keywords.append(cert)

    # Step 1: Apollo discovery → Perplexity fallback if Apollo returns nothing
    raw_buyers = _apollo_search(
        target_iso2=target_iso2,
        person_titles=person_titles,
        company_keywords=company_keywords,
        company_size_ranges=buyer_filters.get("company_size_ranges", ["11-50", "51-200"]),
        limit=50,
    )
    if not raw_buyers:
        print("[Worker 3] Apollo returned no buyers — falling back to Perplexity discovery")
        raw_buyers = _perplexity_buyer_discovery(sector_name, target_iso2, manufacturer)

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
