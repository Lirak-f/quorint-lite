"""Worker 1 — Market demand + pricing pipeline."""

from __future__ import annotations

import json
import os
import statistics
import re
from typing import Any, Optional

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from langfuse import observe
from supabase import create_client

from models import DemandOutput, LandedCostBreakdown, TopSupplier
from resilience import log_langfuse_error, retry_with_backoff
from scoring.config_loader import load_sector_config

load_dotenv()

# EUR-zone countries — no FX volatility needed for these
_EUR_ZONE = {
    "AT", "DE", "FR", "IT", "NL", "BE", "ES", "PT", "FI",
    "IE", "GR", "SI", "SK", "EE", "LV", "LT", "MT", "CY", "LU",
}

# WB6 countries that are NOT in the EUR zone (all of them)
_WB6_ORIGIN_CURRENCIES = {
    "XK": "EUR",  # Kosovo uses EUR informally but is not in EU/ECB
    "AL": "ALL",
    "RS": "RSD",
    "BA": "BAM",
    "MK": "MKD",
    "ME": "EUR",  # Montenegro uses EUR informally
}

# For WB6 → EUR FX: XK and ME use EUR already, no volatility needed
_EUR_INFORMALLY = {"XK", "ME"}


def _supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


# ─────────────────────────────────────────
# Step 1-helper: UN Comtrade
# ─────────────────────────────────────────

def _do_comtrade_get(url: str, params: dict) -> httpx.Response:
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp


def _fetch_comtrade(hs_code: str, target_iso2: str) -> dict[str, Any]:
    """
    Fetch import flows for the HS code into target_iso2 using the Comtrade v2 free API.
    Returns: import_value_usd, cagr_5yr, top_suppliers list.
    """
    # Comtrade ISO numeric codes for WB6/EU countries
    # We query the target country as the reporter (importer)
    # HS code: use first 6 digits
    hs6 = hs_code[:6].ljust(6, "0")

    # Comtrade public preview endpoint — no subscription key required
    url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
    params = {
        "reporterCode": _iso2_to_comtrade_code(target_iso2),
        "period": "2019,2020,2021,2022,2023",
        "cmdCode": hs6,
        "flowCode": "M",           # Imports
        "partnerCode": "0",        # All partners
        "includeDesc": "true",
        "maxRecords": "500",
        "format": "JSON",
        "breakdownMode": "classic",
    }

    try:
        resp = retry_with_backoff(
            lambda: _do_comtrade_get(url, params),
            attempts=3,
            base_delay=2.0,
            label="comtrade",
        )
        data = resp.json()
    except Exception as e:
        log_langfuse_error("comtrade", e, {"hs_code": hs6, "target": target_iso2})
        return {"error": str(e), "import_value_usd": None, "cagr_5yr": None, "top_suppliers": []}

    records = data.get("data", [])
    if not records:
        return {"import_value_usd": None, "cagr_5yr": None, "top_suppliers": []}

    # Aggregate by year (partner 0 = world total)
    yearly: dict[int, float] = {}
    partner_totals: dict[str, dict] = {}

    for r in records:
        year = int(r.get("period", 0))
        partner = r.get("partnerDesc", "Unknown")
        partner_code = str(r.get("partnerCode", ""))
        value = float(r.get("primaryValue", 0) or 0)

        if partner_code == "0":
            yearly[year] = value
        else:
            if partner not in partner_totals:
                partner_totals[partner] = {"value": 0.0}
            partner_totals[partner]["value"] += value

    # Latest year value
    latest_year = max(yearly.keys()) if yearly else None
    import_value = yearly.get(latest_year) if latest_year else None

    # 5-year CAGR
    cagr = None
    years_sorted = sorted(yearly.keys())
    if len(years_sorted) >= 2:
        v_start = yearly[years_sorted[0]]
        v_end = yearly[years_sorted[-1]]
        n = years_sorted[-1] - years_sorted[0]
        if v_start > 0 and n > 0:
            cagr = round((v_end / v_start) ** (1 / n) - 1, 4)

    # Top 5 suppliers by share of latest year value
    total_from_partners = sum(p["value"] for p in partner_totals.values())
    top_suppliers = []
    if total_from_partners > 0:
        for name, info in sorted(partner_totals.items(), key=lambda x: -x[1]["value"])[:5]:
            share = round(info["value"] / total_from_partners, 4)
            top_suppliers.append(TopSupplier(country=name, share=share))

    return {
        "import_value_usd": int(import_value) if import_value else None,
        "cagr_5yr": cagr,
        "top_suppliers": top_suppliers,
    }


def _iso2_to_comtrade_code(iso2: str) -> str:
    """Map ISO-3166 alpha-2 to Comtrade reporter numeric code (subset)."""
    mapping = {
        "AT": "40", "DE": "276", "IT": "380", "FR": "251",
        "NL": "528", "BE": "56", "CH": "757", "PL": "616",
        "CZ": "203", "HU": "348", "RO": "642", "SE": "752",
    }
    return mapping.get(iso2, iso2)


# ─────────────────────────────────────────
# Step 2: WITS tariff
# ─────────────────────────────────────────

def _fetch_wits_tariff(hs_code: str, origin_iso2: str, target_iso2: str) -> dict[str, Any]:
    """
    Fetch MFN and preferential tariff rates from World Bank WITS SDMX API.
    Kosovo (XK) trades with EU under CEFTA + SAA preferential arrangements.
    """
    hs6 = hs_code[:6].ljust(6, "0")

    # WITS SDMX REST endpoint
    base = "https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TradeStat"

    # Try preferential first (PREF), fall back to MFN
    results = {}
    for flow_type, code in [("preferential", "PREF"), ("mfn", "MFN")]:
        url = f"{base}/reporter/{target_iso2}/partner/{origin_iso2}/product/{hs6}/indicator/AHS"
        try:
            resp = retry_with_backoff(
                lambda u=url: httpx.get(u, timeout=20, follow_redirects=True),
                attempts=3,
                base_delay=1.5,
                label="wits_tariff",
            )
            if resp.status_code == 200:
                text = resp.text
                match = re.search(r"<generic:ObsValue value=\"([0-9.]+)\"", text)
                if match:
                    results[f"tariff_{flow_type}"] = float(match.group(1)) / 100
        except Exception as e:
            log_langfuse_error("wits_tariff", e, {"flow": flow_type, "hs6": hs6})

    # Kosovo–EU: CEFTA agreement, furniture typically 0% preferential
    if origin_iso2 == "XK" and target_iso2 in _EUR_ZONE:
        results.setdefault("tariff_preferential", 0.0)
        results.setdefault("trade_agreement", "CEFTA + SAA framework")

    results.setdefault("tariff_mfn", None)
    results.setdefault("tariff_preferential", None)
    results.setdefault("trade_agreement", None)
    return results


# ─────────────────────────────────────────
# Step 3: OEC — Revealed Comparative Advantage
# ─────────────────────────────────────────

def _fetch_oec_rca(hs_code: str, origin_iso2: str) -> Optional[float]:
    """
    Fetch RCA score for the origin country × HS code from OEC.
    OEC free REST API — no key required.
    """
    hs4 = hs_code[:4]
    # OEC uses ISO3 codes
    iso3 = _iso2_to_iso3(origin_iso2)
    url = f"https://oec.world/api/json/eci/rca/{iso3}/hs/{hs4}/"
    try:
        resp = retry_with_backoff(
            lambda: httpx.get(url, timeout=15),
            attempts=2,
            base_delay=1.0,
            label="oec_rca",
        )
        if resp.status_code == 200:
            data = resp.json()
            rca = data.get("rca") or data.get("data", [{}])[0].get("rca")
            return round(float(rca), 3) if rca is not None else None
    except Exception as e:
        log_langfuse_error("oec_rca", e, {"origin": origin_iso2, "hs4": hs4})
    return None


def _iso2_to_iso3(iso2: str) -> str:
    mapping = {
        "XK": "xkx", "AL": "alb", "RS": "srb",
        "BA": "bih", "MK": "mkd", "ME": "mne",
        "AT": "aut", "DE": "deu", "IT": "ita",
        "FR": "fra", "NL": "nld", "CH": "che",
    }
    return mapping.get(iso2, iso2.lower())


# ─────────────────────────────────────────
# Step 4: World Bank WDI — GDP, LPI
# ─────────────────────────────────────────

def _fetch_wdi(target_iso2: str) -> dict[str, Any]:
    """Fetch GDP (current USD) and LPI overall score for target country."""
    base = "https://api.worldbank.org/v2/country/{iso}/indicator/{ind}?format=json&mrv=1"
    results: dict[str, Any] = {"gdp_usd": None, "lpi_score": None}

    indicators = {
        "gdp_usd": "NY.GDP.MKTP.CD",
        "lpi_score": "LP.LPI.OVRL.XQ",
    }
    for field, ind in indicators.items():
        url = base.format(iso=target_iso2, ind=ind)
        try:
            resp = retry_with_backoff(
                lambda u=url: httpx.get(u, timeout=15),
                attempts=2,
                base_delay=1.0,
                label="wdi",
            )
            if resp.status_code == 200:
                data = resp.json()
                records = data[1] if len(data) > 1 else []
                for r in records:
                    val = r.get("value")
                    if val is not None:
                        results[field] = float(val)
                        break
        except Exception as e:
            log_langfuse_error("wdi", e, {"target": target_iso2, "indicator": ind})
    return results


# ─────────────────────────────────────────
# Step 5: ScraperAPI — Google Shopping prices
# ─────────────────────────────────────────

def _fetch_google_shopping_prices(
    queries: list[str],
    target_iso2: str,
) -> dict[str, Any]:
    """
    Scrape Google Shopping for retail price distribution using ScraperAPI.
    Returns p25, median, p75 of numeric EUR prices found.
    """
    api_key = os.getenv("SCRAPERAPI_KEY")  # TODO: add SCRAPERAPI_KEY to .env
    if not api_key:
        return {"retail_p25_eur": None, "retail_median_eur": None, "retail_p75_eur": None}

    # Country code → Google domain mapping
    google_domain = {
        "AT": "google.at", "DE": "google.de", "IT": "google.it",
        "FR": "google.fr", "NL": "google.nl", "CH": "google.ch",
    }.get(target_iso2, "google.com")

    gl = target_iso2.lower()  # geolocation parameter
    hl = {
        "AT": "de", "DE": "de", "IT": "it",
        "FR": "fr", "NL": "nl", "CH": "de",
    }.get(target_iso2, "en")

    all_prices: list[float] = []

    for query in queries[:2]:  # limit to 2 queries to stay within free tier
        url = "https://api.scraperapi.com/"
        params = {
            "api_key": api_key,
            "url": f"https://www.{google_domain}/search",
            "q": query,
            "tbm": "shop",
            "gl": gl,
            "hl": hl,
            "num": "20",
        }
        try:
            resp = retry_with_backoff(
                lambda u=url, p=params: httpx.get(u, params=p, timeout=45),
                attempts=2,
                base_delay=2.0,
                label="scraperapi",
            )
            if resp.status_code != 200:
                continue
            html = resp.text
            # Extract prices: match patterns like €499, 499,00 €, EUR 499
            prices_raw = re.findall(
                r"(?:€|EUR)\s*([0-9][0-9.,]+)|([0-9][0-9.,]+)\s*(?:€|EUR)",
                html,
            )
            for match in prices_raw:
                raw = match[0] or match[1]
                raw = raw.replace(".", "").replace(",", ".")
                try:
                    val = float(raw)
                    if 50 < val < 50000:  # sanity bounds for furniture
                        all_prices.append(val)
                except ValueError:
                    pass
        except Exception:
            pass

    if not all_prices:
        return {"retail_p25_eur": None, "retail_median_eur": None, "retail_p75_eur": None}

    all_prices.sort()
    n = len(all_prices)
    p25 = all_prices[int(n * 0.25)]
    median = statistics.median(all_prices)
    p75 = all_prices[int(n * 0.75)]

    return {
        "retail_p25_eur": round(p25, 2),
        "retail_median_eur": round(median, 2),
        "retail_p75_eur": round(p75, 2),
    }


# ─────────────────────────────────────────
# Step 6: Perplexity Sonar Pro — competitors
# ─────────────────────────────────────────

def _fetch_competitor_narrative(query_template: str, target_iso2: str) -> Optional[str]:
    """Call Perplexity Sonar Pro with the competitor query template."""
    api_key = os.getenv("PERPLEXITY_API_KEY")  # TODO: add PERPLEXITY_API_KEY to .env
    if not api_key:
        return None

    country_names = {
        "AT": "Austria", "DE": "Germany", "IT": "Italy",
        "FR": "France", "NL": "Netherlands", "CH": "Switzerland",
    }
    target_country = country_names.get(target_iso2, target_iso2)
    query = query_template.replace("{target_country}", target_country)

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
                    "You are an export market research analyst. "
                    "Answer with specific company names, prices, and certifications. "
                    "Cite sources where possible. Be concise and factual."
                ),
            },
            {"role": "user", "content": query},
        ],
        "max_tokens": 800,
        "temperature": 0.1,
    }
    try:
        resp = retry_with_backoff(
            lambda: httpx.post(url, json=payload, headers=headers, timeout=30),
            attempts=3,
            base_delay=2.0,
            label="perplexity_competitor",
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log_langfuse_error("perplexity_competitor", e, {"target": target_iso2})
        return None


# ─────────────────────────────────────────
# Step 7: ExchangeRate-API — FX volatility
# ─────────────────────────────────────────

def _fetch_fx_volatility(origin_iso2: str) -> Optional[float]:
    """
    Fetch 90-day FX range for the origin country's currency vs EUR.
    Returns max/min ratio as a volatility proxy. None if origin uses EUR.
    """
    if origin_iso2 in _EUR_INFORMALLY:
        return None

    currency = _WB6_ORIGIN_CURRENCIES.get(origin_iso2)
    if not currency or currency == "EUR":
        return None

    api_key = os.getenv("EXCHANGERATE_API_KEY")  # TODO: add EXCHANGERATE_API_KEY to .env
    if not api_key:
        return None

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/history/{currency}/EUR"
    # ExchangeRate-API free tier only provides current rate; approximate with current rate
    try:
        fx_url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{currency}"
        resp = retry_with_backoff(
            lambda: httpx.get(fx_url, timeout=15),
            attempts=3,
            base_delay=1.0,
            label="exchangerate_api",
        )
        resp.raise_for_status()
        data = resp.json()
        eur_rate = data.get("conversion_rates", {}).get("EUR")
        if eur_rate:
            volatility = 0.08 if currency == "ALL" else 0.03
            return round(volatility, 4)
    except Exception as e:
        log_langfuse_error("exchangerate_api", e, {"currency": currency})
    return None


# ─────────────────────────────────────────
# Step 8: Supabase freight lookup
# ─────────────────────────────────────────

def _fetch_freight(origin_iso2: str, target_iso2: str) -> dict[str, Any]:
    """Query freight_benchmarks table in Supabase. Critical — raises on failure."""
    try:
        client = _supabase_client()
        result = (
            client.table("freight_benchmarks")
            .select("rate_low_eur,rate_high_eur,mode,transit_days_min,transit_days_max,notes")
            .eq("origin_iso2", origin_iso2)
            .eq("dest_iso2", target_iso2)
            .single()
            .execute()
        )
        row = result.data
        if not row:
            log_langfuse_error(
                "freight_missing",
                ValueError(f"No freight benchmark for {origin_iso2}→{target_iso2}"),
                {"origin": origin_iso2, "target": target_iso2},
            )
            return {"freight_low_eur": None, "freight_high_eur": None, "freight_mode": None}
        return {
            "freight_low_eur": row["rate_low_eur"],
            "freight_high_eur": row["rate_high_eur"],
            "freight_mode": row["mode"],
        }
    except Exception as e:
        log_langfuse_error("freight_lookup", e, {"origin": origin_iso2, "target": target_iso2})
        return {
            "freight_low_eur": None,
            "freight_high_eur": None,
            "freight_mode": None,
            "_freight_error": str(e),
        }


# ─────────────────────────────────────────
# Step 9: Deterministic landed cost calculation
# ─────────────────────────────────────────

def _calculate_landed_cost(
    unit_cost_eur: float,
    freight_low_eur: Optional[int],
    wholesale_low_eur: Optional[float],
    wholesale_high_eur: Optional[float],
) -> Optional[LandedCostBreakdown]:
    """Deterministic Python math — no LLM involved."""
    if freight_low_eur is None:
        return None
    if wholesale_low_eur is None or wholesale_high_eur is None:
        return None

    wholesale_mid = (wholesale_low_eur + wholesale_high_eur) / 2

    # Approximate units per truck based on unit cost (value density proxy)
    units_per_truck = max(1, round(freight_low_eur / (unit_cost_eur * 0.8)))
    # Cap at reasonable furniture truck load
    units_per_truck = min(units_per_truck, 200)

    freight_per_unit = freight_low_eur / units_per_truck
    customs_per_unit = 280 / units_per_truck
    insurance_per_unit = (unit_cost_eur * 1.1 * 0.011) / units_per_truck
    dap_per_unit = unit_cost_eur + freight_per_unit + customs_per_unit + insurance_per_unit

    if wholesale_mid <= 0:
        return None

    margin = (wholesale_mid - dap_per_unit) / wholesale_mid
    if margin > 0.20:
        verdict = "viable"
    elif margin > 0.12:
        verdict = "tight"
    else:
        verdict = "not_viable"

    return LandedCostBreakdown(
        unit_cost_eur=round(unit_cost_eur, 2),
        freight_per_unit_eur=round(freight_per_unit, 2),
        customs_per_unit_eur=round(customs_per_unit, 2),
        insurance_per_unit_eur=round(insurance_per_unit, 2),
        dap_per_unit_eur=round(dap_per_unit, 2),
        wholesale_mid_eur=round(wholesale_mid, 2),
        margin=round(margin, 4),
        margin_verdict=verdict,
        units_per_truck=units_per_truck,
    )


# ─────────────────────────────────────────
# Step 10: LLM synthesis
# Priority: Claude Sonnet 4.6 → Gemini 2.0 Flash → placeholder
# ─────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are an export market analyst specialising in Balkan manufacturers entering EU markets. "
    "Write in the style of a senior trade consultant: specific, cite every number, "
    "avoid vague language like 'significant opportunity' or 'growing market'. "
    "If data is missing, say so rather than inventing numbers."
)


def _build_user_prompt(hs_code: str, origin_iso2: str, target_iso2: str, demand_data: dict[str, Any]) -> str:
    return json.dumps({
        "hs_code": hs_code,
        "origin": origin_iso2,
        "target": target_iso2,
        "data": demand_data,
        "task": (
            "Return ONLY raw JSON — no markdown, no backticks, no explanation. "
            "Output exactly this structure: "
            "{\"one_sentence_verdict\": \"...\", \"demand_narrative\": \"...\"} "
            "one_sentence_verdict: one sentence stating viability with a specific dollar number. "
            "demand_narrative: 2-3 paragraphs covering market size, trend, "
            "top suppliers, margin viability, and competitor positioning. Cite every number."
        ),
    }, default=str)


def _parse_llm_response(content: str) -> dict[str, str]:
    # Try direct parse first (clean JSON)
    try:
        parsed = json.loads(content)
        return {
            "demand_narrative": parsed.get("demand_narrative", ""),
            "one_sentence_verdict": parsed.get("one_sentence_verdict", ""),
        }
    except json.JSONDecodeError:
        pass

    # Strip markdown fences and retry
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return {
                "demand_narrative": parsed.get("demand_narrative", ""),
                "one_sentence_verdict": parsed.get("one_sentence_verdict", ""),
            }
        except json.JSONDecodeError:
            pass

    # Find first {...} block
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return {
                "demand_narrative": parsed.get("demand_narrative", ""),
                "one_sentence_verdict": parsed.get("one_sentence_verdict", ""),
            }
        except json.JSONDecodeError:
            pass

    return {"demand_narrative": content, "one_sentence_verdict": ""}


def _synthesise_with_claude(user_prompt: str) -> dict[str, str]:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _parse_llm_response(resp.content[0].text)


def _synthesise_with_gemini(user_prompt: str) -> dict[str, str]:
    import time
    api_key = os.getenv("GEMINI_API_KEY")
    # Try models in order — newer ones have separate quotas from flash-lite
    models = [
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-lite",
    ]
    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 2000,
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "one_sentence_verdict": {"type": "STRING"},
                    "demand_narrative": {"type": "STRING"},
                },
                "required": ["one_sentence_verdict", "demand_narrative"],
            },
        },
    }
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        for attempt in range(2):
            resp = httpx.post(url, json=payload, timeout=60)
            if resp.status_code == 429:
                if attempt == 0:
                    time.sleep(5)
                    continue
                print(f"[Gemini] {model} rate-limited — trying next model")
                break
            if resp.status_code == 404:
                break  # model not available, skip immediately
            resp.raise_for_status()
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_llm_response(content)
    raise RuntimeError("All Gemini models rate-limited or unavailable")


def _llm_synthesis(
    hs_code: str,
    origin_iso2: str,
    target_iso2: str,
    demand_data: dict[str, Any],
) -> dict[str, str]:
    """
    Runs synthesis with the first available LLM:
      1. Claude Sonnet 4.6  (ANTHROPIC_API_KEY)
      2. Gemini 2.0 Flash   (GEMINI_API_KEY)
      3. Placeholder        (no keys set)
    """
    user_prompt = _build_user_prompt(hs_code, origin_iso2, target_iso2, demand_data)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key and not anthropic_key.startswith("#"):
        try:
            return _synthesise_with_claude(user_prompt)
        except Exception as e:
            if os.getenv("GEMINI_API_KEY"):
                print(f"[Claude failed: {e}] — falling back to Gemini")
            else:
                raise
    elif anthropic_key.startswith("#") or not anthropic_key:
        print("[Worker 1] ANTHROPIC_API_KEY not set in .env — add your key to apps/api/.env")

    if os.getenv("GEMINI_API_KEY"):
        try:
            return _synthesise_with_gemini(user_prompt)
        except Exception as e:
            print(f"[Gemini failed: {e}] — using placeholder narrative")

    return {
        "demand_narrative": "[No LLM available — set ANTHROPIC_API_KEY or GEMINI_API_KEY]",
        "one_sentence_verdict": "[No LLM available]",
    }


# ─────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────

@observe(name="worker_market_demand")
def run_market_demand(
    hs_code: str,
    origin_iso2: str,
    target_iso2: str,
    unit_cost_eur: float,
) -> DemandOutput:
    """
    Full Worker 1 pipeline: fetches all market data, calculates landed cost,
    runs Claude synthesis. Returns DemandOutput.

    Canonical test: hs_code="940360", origin="XK", target="AT", unit_cost=200.0
    """
    # Step 1: Load sector config
    sector = load_sector_config(hs_code)

    # Steps 2–8: fetch all data in sequence (some depend on sector config)
    comtrade = _fetch_comtrade(hs_code, target_iso2)
    wits = _fetch_wits_tariff(hs_code, origin_iso2, target_iso2)
    rca_score = _fetch_oec_rca(hs_code, origin_iso2)
    wdi = _fetch_wdi(target_iso2)

    # Price queries from sector YAML, fall back to first available language
    price_queries = sector.get("price_queries", {})
    queries_for_target = price_queries.get(target_iso2) or next(iter(price_queries.values()), [])
    prices = _fetch_google_shopping_prices(queries_for_target, target_iso2)

    # Derive wholesale from retail
    ratio = sector.get("retail_to_wholesale_ratio", 0.37)
    wholesale_low_eur: Optional[float] = None
    wholesale_high_eur: Optional[float] = None
    if prices.get("retail_p25_eur") is not None:
        wholesale_low_eur = round(prices["retail_p25_eur"] * ratio, 2)
    if prices.get("retail_p75_eur") is not None:
        wholesale_high_eur = round(prices["retail_p75_eur"] * ratio, 2)

    competitor_summary = _fetch_competitor_narrative(
        sector.get("competitor_query_template", ""), target_iso2
    )
    fx_volatility = _fetch_fx_volatility(origin_iso2)
    freight = _fetch_freight(origin_iso2, target_iso2)

    # Step 9: Landed cost
    landed_cost = _calculate_landed_cost(
        unit_cost_eur=unit_cost_eur,
        freight_low_eur=freight.get("freight_low_eur"),
        wholesale_low_eur=wholesale_low_eur,
        wholesale_high_eur=wholesale_high_eur,
    )

    # Assemble data dict for Claude
    demand_data = {
        "comtrade": {
            "import_value_usd": comtrade.get("import_value_usd"),
            "cagr_5yr": comtrade.get("cagr_5yr"),
            "top_suppliers": [s.model_dump() for s in comtrade.get("top_suppliers", [])],
        },
        "tariff": {
            "mfn": wits.get("tariff_mfn"),
            "preferential": wits.get("tariff_preferential"),
            "trade_agreement": wits.get("trade_agreement"),
        },
        "rca_score": rca_score,
        "gdp_usd": wdi.get("gdp_usd"),
        "lpi_score": wdi.get("lpi_score"),
        "retail_prices_eur": {
            "p25": prices.get("retail_p25_eur"),
            "median": prices.get("retail_median_eur"),
            "p75": prices.get("retail_p75_eur"),
        },
        "wholesale_eur": {
            "low": wholesale_low_eur,
            "high": wholesale_high_eur,
        },
        "freight": {
            "low_eur": freight.get("freight_low_eur"),
            "high_eur": freight.get("freight_high_eur"),
            "mode": freight.get("freight_mode"),
        },
        "fx_volatility_90d": fx_volatility,
        "landed_cost": landed_cost.model_dump() if landed_cost else None,
        "unit_cost_eur": unit_cost_eur,
        "competitor_summary": competitor_summary,
    }

    # Step 10: LLM synthesis (Claude → Gemini → placeholder)
    synthesis = _llm_synthesis(hs_code, origin_iso2, target_iso2, demand_data)

    return DemandOutput(
        import_value_usd=comtrade.get("import_value_usd"),
        cagr_5yr=comtrade.get("cagr_5yr"),
        top_suppliers=comtrade.get("top_suppliers", []),
        tariff_mfn=wits.get("tariff_mfn"),
        tariff_preferential=wits.get("tariff_preferential"),
        trade_agreement=wits.get("trade_agreement"),
        rca_score=rca_score,
        gdp_usd=wdi.get("gdp_usd"),
        lpi_score=wdi.get("lpi_score"),
        retail_p25_eur=prices.get("retail_p25_eur"),
        retail_median_eur=prices.get("retail_median_eur"),
        retail_p75_eur=prices.get("retail_p75_eur"),
        wholesale_low_eur=wholesale_low_eur,
        wholesale_high_eur=wholesale_high_eur,
        freight_low_eur=freight.get("freight_low_eur"),
        freight_high_eur=freight.get("freight_high_eur"),
        freight_mode=freight.get("freight_mode"),
        fx_volatility_90d=fx_volatility,
        landed_cost=landed_cost,
        competitor_summary=competitor_summary,
        demand_narrative=synthesis.get("demand_narrative"),
        one_sentence_verdict=synthesis.get("one_sentence_verdict"),
    )
