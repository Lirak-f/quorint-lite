"""Worker 4 — Deep market research via Perplexity Sonar Deep Research API."""

from __future__ import annotations

import os
import re
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from langfuse import observe

from models import DeepResearchOutput

load_dotenv()

_COUNTRY_NAMES = {
    "AT": "Austria", "DE": "Germany", "IT": "Italy",
    "FR": "France", "NL": "Netherlands", "CH": "Switzerland",
    "BE": "Belgium", "PL": "Poland", "ES": "Spain",
}

_ORIGIN_NAMES = {
    "XK": "Kosovo", "AL": "Albania", "RS": "Serbia",
    "BA": "Bosnia and Herzegovina", "MK": "North Macedonia", "ME": "Montenegro",
}

_PRODUCT_DESCRIPTIONS = {
    "94": "wooden furniture (solid oak dining tables and chairs)",
    "44": "wood and wood products",
    "61": "knitted apparel and clothing",
    "62": "woven apparel and clothing",
    "63": "textile home furnishings",
    "84": "industrial machinery and equipment",
    "85": "electrical machinery and equipment",
    "87": "automotive parts and components",
    "72": "steel and iron products",
    "73": "steel articles and fabricated metal products",
    "15": "vegetable oils and fats",
    "16": "prepared meat and fish products",
    "20": "prepared vegetables and fruit products",
    "21": "miscellaneous food preparations",
    "22": "beverages and spirits",
}


def _get_product_description(hs_code: str) -> str:
    chapter = hs_code[:2].zfill(2)
    return _PRODUCT_DESCRIPTIONS.get(chapter, f"manufactured goods (HS {hs_code})")


def _build_deep_research_query(
    hs_code: str,
    origin_iso2: str,
    target_iso2: str,
) -> str:
    product_desc = _get_product_description(hs_code)
    target_country = _COUNTRY_NAMES.get(target_iso2, target_iso2)
    origin_country = _ORIGIN_NAMES.get(origin_iso2, origin_iso2)

    return (
        f"Provide a comprehensive market analysis for {product_desc} "
        f"(HS code {hs_code}) in {target_country}. Cover:\n\n"
        f"1. Distribution structure — who are the key wholesale channels? "
        f"Name actual companies, not generic categories.\n\n"
        f"2. Buyer behaviour — how do {target_country} distributors evaluate "
        f"and onboard new foreign suppliers? What do they need to see first?\n\n"
        f"3. Cultural/business norms — what matters to {target_country} buyers "
        f"when dealing with {origin_country} manufacturers specifically?\n\n"
        f"4. Recent sector developments in 2024-2025 — regulatory changes, "
        f"demand shifts, new market entrants.\n\n"
        f"5. Seasonal patterns — when do buyers place orders for this category?\n\n"
        f"6. What differentiates foreign manufacturers who succeed in {target_country} "
        f"from those who fail? Be specific.\n\n"
        f"7. Any named distributors or wholesalers not already in commercial databases "
        f"(smaller, regional, or niche operators).\n\n"
        "Cite all sources. Be specific and concrete throughout."
    )


def _extract_additional_buyers(narrative: str, target_iso2: str) -> list[dict[str, Any]]:
    """
    Parse company names mentioned in the deep research narrative.
    Returns lightweight dicts for buyers not likely in Apollo/PDL.
    """
    buyers: list[dict[str, Any]] = []

    # Match patterns like "Company Name GmbH", "XYZ AG", "ABC S.r.l.", "DEF S.A."
    company_patterns = [
        r"\b([A-Z][A-Za-z\s&'-]+(?:GmbH|AG|KG|OHG|GmbH & Co\. KG|S\.r\.l\.|S\.A\.|BV|NV|Ltd|S\.p\.A\.))\b",
        r"\b([A-Z][A-Za-z\s&'-]{3,40}(?:Handel|Möbel|Furniture|Wood|Holz|Import|Wholesale|Trading))\b",
    ]

    seen: set[str] = set()
    for pattern in company_patterns:
        for match in re.finditer(pattern, narrative):
            name = match.group(1).strip()
            if len(name) > 5 and name not in seen:
                seen.add(name)
                buyers.append({
                    "company_name": name,
                    "country_iso2": target_iso2,
                    "enrichment_source": "perplexity",
                    "source": "deep_research_narrative",
                })

    return buyers[:10]  # cap at 10 to avoid noise


def _call_perplexity_deep_research(query: str) -> dict[str, Any]:
    """Call Perplexity sonar-deep-research API and return raw response dict."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key or api_key.startswith("#"):
        return {"narrative": None, "error": "PERPLEXITY_API_KEY not set"}

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "sonar-deep-research",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior export market analyst with deep expertise in European B2B distribution. "
                    "Provide detailed, cite-rich market intelligence. "
                    "Name specific companies, cite specific regulations, give specific numbers. "
                    "Structure your response with clear numbered sections matching the query."
                ),
            },
            {"role": "user", "content": query},
        ],
        "max_tokens": 4000,
        "temperature": 0.1,
    }

    try:
        # sonar-deep-research can take ~3 minutes — use a 240s timeout
        resp = httpx.post(url, json=payload, headers=headers, timeout=240)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Extract citations if present
        citations = data.get("citations", [])
        if not citations:
            # Try to extract source URLs from the content itself
            citations = re.findall(r"https?://[^\s\)\"']+", content)[:15]

        return {"narrative": content, "citations": citations, "error": None}

    except httpx.TimeoutException:
        return {"narrative": None, "error": "Perplexity deep research timed out (>240s)"}
    except httpx.HTTPStatusError as e:
        return {"narrative": None, "error": f"Perplexity HTTP error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"narrative": None, "error": str(e)}


def _call_perplexity_sonar_fallback(query: str) -> dict[str, Any]:
    """Fallback to sonar-pro if deep-research is unavailable or times out."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key or api_key.startswith("#"):
        return {"narrative": None, "error": "PERPLEXITY_API_KEY not set"}

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior export market analyst. Be specific: name companies, cite regulations, "
                    "give numbers. Address all 7 topics in the query."
                ),
            },
            {"role": "user", "content": query},
        ],
        "max_tokens": 2500,
        "temperature": 0.1,
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        citations = data.get("citations", re.findall(r"https?://[^\s\)\"']+", content)[:10])
        return {"narrative": content, "citations": citations, "error": None, "model_used": "sonar-pro-fallback"}
    except Exception as e:
        return {"narrative": None, "error": f"sonar-pro fallback error: {e}"}


def _call_gemini_fallback(query: str, hs_code: str, origin_iso2: str, target_iso2: str) -> dict[str, Any]:
    """Final fallback to Gemini when Perplexity is unavailable."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        return {"narrative": None, "error": "No LLM available for deep research"}

    product_desc = _get_product_description(hs_code)
    target_country = _COUNTRY_NAMES.get(target_iso2, target_iso2)
    origin_country = _ORIGIN_NAMES.get(origin_iso2, origin_iso2)

    models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    "You are a senior export market analyst. Be specific: name companies, cite EU regulations, "
                    "give concrete numbers. Focus on actionable intelligence."
                )
            }]
        },
        "contents": [{"parts": [{"text": query}]}],
        "generationConfig": {
            "maxOutputTokens": 3000,
            "temperature": 0.2,
        },
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = httpx.post(url, json=payload, timeout=90)
            if resp.status_code in (429, 404):
                continue
            resp.raise_for_status()
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            if content:
                return {"narrative": content, "citations": [], "error": None, "model_used": f"gemini-{model}-fallback"}
        except Exception as e:
            print(f"[Worker 4] Gemini {model} error: {e}")
            continue

    return {"narrative": None, "error": "All LLM fallbacks exhausted for deep research"}


@observe(name="worker_deep_research")
def run_deep_research(
    hs_code: str,
    origin_iso2: str,
    target_iso2: str,
) -> DeepResearchOutput:
    """
    Worker 4: calls Perplexity Sonar Deep Research for comprehensive market narrative.
    Falls back to sonar-pro then Gemini if deep-research is unavailable.

    Canonical test: hs_code="940360", origin="XK", target="AT"
    """
    query = _build_deep_research_query(hs_code, origin_iso2, target_iso2)

    print(f"[Worker 4] Starting deep research for HS {hs_code} {origin_iso2}→{target_iso2}")

    # Primary: Perplexity sonar-deep-research
    result = _call_perplexity_deep_research(query)

    if result.get("error") or not result.get("narrative"):
        print(f"[Worker 4] sonar-deep-research failed ({result.get('error')}) — falling back to sonar-pro")
        result = _call_perplexity_sonar_fallback(query)

    if result.get("error") or not result.get("narrative"):
        print(f"[Worker 4] sonar-pro failed ({result.get('error')}) — falling back to Gemini")
        result = _call_gemini_fallback(query, hs_code, origin_iso2, target_iso2)

    narrative = result.get("narrative") or "[Deep research unavailable — all providers failed]"
    citations = result.get("citations", [])
    model_used = result.get("model_used", "sonar-deep-research")

    if result.get("model_used"):
        print(f"[Worker 4] Used fallback model: {model_used}")

    # Extract any additional buyer names mentioned in the narrative
    additional_buyers = _extract_additional_buyers(narrative, target_iso2)
    if additional_buyers:
        print(f"[Worker 4] Extracted {len(additional_buyers)} additional buyer names from narrative")

    return DeepResearchOutput(
        market_narrative=narrative,
        sources=citations,
        additional_buyers=additional_buyers,
    )
