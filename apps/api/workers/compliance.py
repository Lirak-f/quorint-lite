"""Worker 2 — Compliance map: certifications, costs, lead times per HS × target country."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from langfuse import observe

from models import ComplianceItem, ComplianceOutput
from scoring.config_loader import load_sector_config

load_dotenv()

# EU member states — used to gate TRACES / EUR-Lex checks
_EU_MEMBERS = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
    "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PL", "PT", "RO", "SE", "SI", "SK",
}

# Food/agri HS chapters that require SPS checks (01–24)
_FOOD_AGRI_CHAPTERS = {str(i).zfill(2) for i in range(1, 25)}

# Food/agri chapters for FDA FSVP (US-only; 07–24)
_FDA_FSVP_CHAPTERS = {str(i).zfill(2) for i in range(7, 25)}

# HS chapters with ECHA / REACH chemical relevance
_CHEMICAL_CHAPTERS = {"28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "64", "65", "73"}


# ─────────────────────────────────────────
# ECHA REST API
# ─────────────────────────────────────────

def _check_echa_reach(hs_code: str) -> dict[str, Any]:
    """
    Query ECHA REST to determine REACH applicability for the given HS chapter.
    Returns a dict describing REACH SVHC obligations if relevant.
    """
    chapter = hs_code[:2].zfill(2)
    if chapter not in _CHEMICAL_CHAPTERS:
        return {"reach_applies": False}

    # ECHA substances of very high concern list (public endpoint)
    url = "https://echa.europa.eu/api/substances/svhc"
    try:
        resp = httpx.get(url, timeout=15)
        if resp.status_code == 200:
            return {"reach_applies": True, "source": "echa_api"}
    except Exception:
        pass

    # Fallback: REACH applies to all chemical-adjacent chapters by regulation
    return {"reach_applies": True, "source": "regulatory_default"}


# ─────────────────────────────────────────
# EU TRACES — SPS certificates
# ─────────────────────────────────────────

def _check_traces_requirement(hs_code: str, target_iso2: str) -> Optional[dict[str, Any]]:
    """
    For food/agri HS chapters into EU member states, TRACES SPS certificate is required.
    Returns a compliance item dict if applicable, None otherwise.
    """
    chapter = hs_code[:2].zfill(2)
    if target_iso2 not in _EU_MEMBERS or chapter not in _FOOD_AGRI_CHAPTERS:
        return None

    return {
        "id": "traces_sps",
        "name": "EU TRACES SPS Certificate",
        "type": "mandatory",
        "critical": True,
        "cost_low_eur": 200,
        "cost_high_eur": 800,
        "lead_time_weeks_min": 2,
        "lead_time_weeks_max": 6,
        "providers": [
            "EU TRACES system (traces.ec.europa.eu)",
            "National competent authority in origin country",
        ],
        "note": (
            "Sanitary and Phytosanitary certificate required for food/agri products "
            "entering the EU. Must be issued by the competent authority in your origin country "
            "before shipment."
        ),
    }


# ─────────────────────────────────────────
# FDA FSVP — US market only
# ─────────────────────────────────────────

def _check_fda_fsvp(hs_code: str, target_iso2: str) -> Optional[dict[str, Any]]:
    """Return FDA FSVP requirement dict if target is US and product is food/agri."""
    if target_iso2 != "US":
        return None
    chapter = hs_code[:2].zfill(2)
    if chapter not in _FDA_FSVP_CHAPTERS:
        return None

    return {
        "id": "fda_fsvp",
        "name": "FDA Foreign Supplier Verification Program (FSVP)",
        "type": "mandatory",
        "critical": True,
        "cost_low_eur": 1500,
        "cost_high_eur": 4000,
        "lead_time_weeks_min": 8,
        "lead_time_weeks_max": 16,
        "providers": [
            "FDA-registered food safety consultant",
            "NSF International (nsf.org)",
            "Bureau Veritas USA",
        ],
        "note": (
            "US importers must establish an FSVP before your first shipment. "
            "Your US buyer is typically responsible, but you must provide supporting documentation. "
            "Coordinate with your US importer early."
        ),
    }


# ─────────────────────────────────────────
# Claude Sonnet 4.6 — compliance synthesis
# ─────────────────────────────────────────

_COMPLIANCE_SYSTEM = (
    "You are a trade compliance specialist with 15 years experience helping manufacturers "
    "enter EU markets. Be precise. Cite specific EU regulation numbers (e.g. Regulation (EU) 2023/1115). "
    "Name specific certification bodies — never say 'contact a notified body', name the actual body "
    "with its city and contact. Costs must be realistic EUR ranges from current market rates. "
    "Lead times must account for realistic queue times at certification bodies. "
    "Flag exactly one item as the single most critical deal-killer."
)

_COMPLIANCE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cert_id": {"type": "string"},
                    "cert_name": {"type": "string"},
                    "cert_type": {"type": "string", "enum": ["mandatory", "commercial_expected", "recommended"]},
                    "critical": {"type": "boolean"},
                    "cost_low_eur": {"type": "integer"},
                    "cost_high_eur": {"type": "integer"},
                    "lead_time_min_weeks": {"type": "integer"},
                    "lead_time_max_weeks": {"type": "integer"},
                    "providers": {"type": "array", "items": {"type": "string"}},
                    "note": {"type": "string"},
                },
                "required": [
                    "cert_id", "cert_name", "cert_type", "critical",
                    "cost_low_eur", "cost_high_eur",
                    "lead_time_min_weeks", "lead_time_max_weeks",
                    "providers", "note",
                ],
            },
        }
    },
    "required": ["items"],
}


def _build_compliance_prompt(
    hs_code: str,
    target_iso2: str,
    checks_from_yaml: list[dict],
    extra_checks: list[dict],
    sector_config: dict,
) -> str:
    country_names = {
        "AT": "Austria", "DE": "Germany", "IT": "Italy",
        "FR": "France", "NL": "Netherlands", "CH": "Switzerland",
        "US": "United States",
    }
    target_country = country_names.get(target_iso2, target_iso2)

    return json.dumps({
        "task": (
            "Review the compliance requirements below and produce a refined JSON list of "
            "3-5 certification/compliance items for this manufacturer. "
            "Enrich each item with specific regulation citations, named providers with contacts, "
            "and realistic cost/lead time from current market rates. "
            "Flag exactly ONE item as critical=true — the single most likely deal-killer if missed. "
            "Remove any items not relevant to this specific HS code and target market."
        ),
        "hs_code": hs_code,
        "target_country": target_country,
        "target_iso2": target_iso2,
        "sector": sector_config.get("sector_name"),
        "compliance_checks_from_yaml": checks_from_yaml,
        "additional_regulatory_checks": extra_checks,
        "output_format": (
            "Return ONLY valid JSON matching the schema: "
            "{\"items\": [{cert_id, cert_name, cert_type, critical, cost_low_eur, cost_high_eur, "
            "lead_time_min_weeks, lead_time_max_weeks, providers: [string], note}]}"
        ),
    }, ensure_ascii=False)


def _parse_compliance_response(content: str) -> list[dict]:
    """Extract JSON items list from Claude response."""
    # Try direct parse first
    try:
        parsed = json.loads(content)
        if "items" in parsed:
            return parsed["items"]
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        pass

    # Extract JSON block from markdown
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed.get("items", [])
        except json.JSONDecodeError:
            pass

    # Find the first { ... } block
    match = re.search(r"(\{.*\})", content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed.get("items", [])
        except json.JSONDecodeError:
            pass

    return []


def _call_claude_compliance(prompt: str) -> list[dict]:
    """Call Claude Sonnet 4.6 with tool-use JSON schema enforcement."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        print("[Worker 2] ANTHROPIC_API_KEY not set — trying Gemini fallback")
        return _call_gemini_compliance(prompt)

    client = Anthropic(api_key=api_key)

    tools = [
        {
            "name": "submit_compliance_checklist",
            "description": "Submit the structured compliance checklist for this manufacturer.",
            "input_schema": _COMPLIANCE_JSON_SCHEMA,
        }
    ]

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=_COMPLIANCE_SYSTEM,
            tools=tools,
            tool_choice={"type": "tool", "name": "submit_compliance_checklist"},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "submit_compliance_checklist":
                return block.input.get("items", [])
    except Exception as e:
        print(f"[Claude compliance error: {e}] — trying Gemini fallback")

    return _call_gemini_compliance(prompt)


def _call_gemini_compliance(prompt: str) -> list[dict]:
    """Gemini fallback for compliance synthesis using responseSchema for reliable JSON."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        return []

    gemini_schema = {
        "type": "OBJECT",
        "properties": {
            "items": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "cert_id": {"type": "STRING"},
                        "cert_name": {"type": "STRING"},
                        "cert_type": {"type": "STRING"},
                        "critical": {"type": "BOOLEAN"},
                        "cost_low_eur": {"type": "INTEGER"},
                        "cost_high_eur": {"type": "INTEGER"},
                        "lead_time_min_weeks": {"type": "INTEGER"},
                        "lead_time_max_weeks": {"type": "INTEGER"},
                        "providers": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "note": {"type": "STRING"},
                    },
                    "required": ["cert_id", "cert_name", "cert_type", "critical",
                                 "cost_low_eur", "cost_high_eur",
                                 "lead_time_min_weeks", "lead_time_max_weeks",
                                 "providers", "note"],
                },
            }
        },
        "required": ["items"],
    }

    models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    payload = {
        "system_instruction": {"parts": [{"text": _COMPLIANCE_SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 2000,
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema,
        },
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = httpx.post(url, json=payload, timeout=45)
            if resp.status_code in (429, 404):
                continue
            resp.raise_for_status()
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            items = _parse_compliance_response(content)
            if items:
                print(f"[Worker 2] Gemini ({model}) returned {len(items)} compliance items")
                return items
        except Exception as e:
            print(f"[Gemini compliance {model} error: {e}]")
            continue

    return []


# ─────────────────────────────────────────
# Build ComplianceOutput from raw items
# ─────────────────────────────────────────

def _items_from_yaml(checks: list[dict]) -> list[dict]:
    """Normalise YAML compliance_checks into the common dict format."""
    items = []
    for c in checks:
        items.append({
            "cert_id": c.get("id", ""),
            "cert_name": c.get("name", ""),
            "cert_type": c.get("type", "recommended"),
            "critical": c.get("critical", False),
            "cost_low_eur": c.get("cost_low_eur", 0),
            "cost_high_eur": c.get("cost_high_eur", 0),
            "lead_time_min_weeks": c.get("lead_time_weeks_min", 0),
            "lead_time_max_weeks": c.get("lead_time_weeks_max", 0),
            "providers": c.get("providers", []),
            "note": c.get("note", ""),
        })
    return items


def _build_compliance_output(raw_items: list[dict]) -> ComplianceOutput:
    """Convert raw item dicts to ComplianceOutput, ensuring exactly one critical flag."""
    items: list[ComplianceItem] = []
    critical_count = 0

    for raw in raw_items:
        try:
            item = ComplianceItem(
                cert_id=raw.get("cert_id", "unknown"),
                cert_name=raw.get("cert_name", "Unknown"),
                cert_type=raw.get("cert_type", "recommended"),
                critical=bool(raw.get("critical", False)),
                cost_low_eur=int(raw.get("cost_low_eur", 0)),
                cost_high_eur=int(raw.get("cost_high_eur", 0)),
                lead_time_min=int(raw.get("lead_time_min_weeks", raw.get("lead_time_min", 0))),
                lead_time_max=int(raw.get("lead_time_max_weeks", raw.get("lead_time_max", 0))),
                providers=raw.get("providers", []),
                note=raw.get("note"),
            )
            if item.critical:
                critical_count += 1
            items.append(item)
        except Exception as e:
            print(f"[compliance item parse error: {e}] — skipping item {raw.get('cert_id')}")

    # Ensure exactly one critical item — if Claude returned 0 or >1, correct it
    if items and critical_count == 0:
        # Flag the first mandatory item, or the first item
        mandatory = [i for i in items if i.cert_type == "mandatory"]
        target = mandatory[0] if mandatory else items[0]
        # Rebuild with critical=True (Pydantic models are immutable by default;
        # we reconstruct to avoid mutation)
        items = [
            ComplianceItem(
                cert_id=i.cert_id,
                cert_name=i.cert_name,
                cert_type=i.cert_type,
                critical=(i.cert_id == target.cert_id),
                cost_low_eur=i.cost_low_eur,
                cost_high_eur=i.cost_high_eur,
                lead_time_min=i.lead_time_min,
                lead_time_max=i.lead_time_max,
                providers=i.providers,
                note=i.note,
            )
            for i in items
        ]
    elif critical_count > 1:
        # Keep only the first one flagged critical
        first_critical_seen = False
        corrected = []
        for i in items:
            if i.critical and not first_critical_seen:
                first_critical_seen = True
                corrected.append(i)
            elif i.critical:
                corrected.append(ComplianceItem(
                    cert_id=i.cert_id, cert_name=i.cert_name, cert_type=i.cert_type,
                    critical=False, cost_low_eur=i.cost_low_eur, cost_high_eur=i.cost_high_eur,
                    lead_time_min=i.lead_time_min, lead_time_max=i.lead_time_max,
                    providers=i.providers, note=i.note,
                ))
            else:
                corrected.append(i)
        items = corrected

    total_low = sum(i.cost_low_eur for i in items)
    total_high = sum(i.cost_high_eur for i in items)
    critical_id = next((i.cert_id for i in items if i.critical), None)

    return ComplianceOutput(
        items=items,
        total_cost_low_eur=total_low,
        total_cost_high_eur=total_high,
        critical_item_id=critical_id,
    )


# ─────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────

@observe(name="worker_compliance")
def run_compliance(
    hs_code: str,
    target_iso2: str,
) -> ComplianceOutput:
    """
    Full Worker 2 pipeline: loads sector YAML, checks regulatory APIs,
    calls Claude Sonnet 4.6 for enriched structured output.
    Returns ComplianceOutput.

    Canonical test: hs_code="940360", target="AT"
    """
    # Step 1: Load sector config → compliance_checks list
    sector = load_sector_config(hs_code)
    yaml_checks = sector.get("compliance_checks", [])
    yaml_items = _items_from_yaml(yaml_checks)

    # Step 2: Conditional regulatory API checks
    extra_checks: list[dict] = []

    # ECHA / REACH — chemical-adjacent HS chapters
    echa_result = _check_echa_reach(hs_code)
    if echa_result.get("reach_applies"):
        # REACH is already in the YAML for furniture; skip duplicate
        chapter = hs_code[:2].zfill(2)
        if chapter in _CHEMICAL_CHAPTERS and chapter not in {"73"}:
            extra_checks.append({
                "cert_id": "reach_svhc_mandatory",
                "cert_name": "REACH SVHC Authorisation (Article 33)",
                "cert_type": "mandatory",
                "critical": False,
                "cost_low_eur": 500,
                "cost_high_eur": 2000,
                "lead_time_min_weeks": 4,
                "lead_time_max_weeks": 12,
                "providers": ["TÜV SÜD", "Bureau Veritas", "Intertek"],
                "note": "Chemical registration required under REACH Regulation (EC) No 1907/2006.",
            })

    # TRACES SPS — food/agri into EU
    traces_item = _check_traces_requirement(hs_code, target_iso2)
    if traces_item:
        extra_checks.append(traces_item)

    # FDA FSVP — US market only
    fda_item = _check_fda_fsvp(hs_code, target_iso2)
    if fda_item:
        extra_checks.append(fda_item)

    # Step 3: Claude Sonnet 4.6 synthesis
    prompt = _build_compliance_prompt(
        hs_code=hs_code,
        target_iso2=target_iso2,
        checks_from_yaml=yaml_items,
        extra_checks=extra_checks,
        sector_config=sector,
    )
    raw_items = _call_claude_compliance(prompt)

    # Fallback: if Claude returns nothing, use YAML data directly
    if not raw_items:
        print("[compliance] Claude returned no items — using YAML data directly")
        raw_items = yaml_items + extra_checks

    return _build_compliance_output(raw_items)
