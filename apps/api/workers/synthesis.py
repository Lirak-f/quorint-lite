"""Worker 5 — Report synthesis: assembles all worker outputs into the final report markdown."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from langfuse import observe

from models import (
    BuyerList,
    BuyerOutput,
    ComplianceOutput,
    DeepResearchOutput,
    DemandOutput,
    ManufacturerInput,
    ReportSynthesis,
    WorkingCapitalEstimate,
)
from scoring.config_loader import load_sector_config
from scoring.working_capital import calculate_working_capital

load_dotenv()

_TARGET_LANGUAGES = {
    "AT": "German", "DE": "German", "CH": "German",
    "IT": "Italian", "FR": "French",
}

_COUNTRY_NAMES = {
    "AT": "Austria", "DE": "Germany", "IT": "Italy",
    "FR": "France", "NL": "Netherlands", "CH": "Switzerland",
}

_ORIGIN_NAMES = {
    "XK": "Kosovo", "AL": "Albania", "RS": "Serbia",
    "BA": "Bosnia and Herzegovina", "MK": "North Macedonia", "ME": "Montenegro",
}


# ─────────────────────────────────────────
# Section 5: First contact kit
# ─────────────────────────────────────────

_SECTION5_SYSTEM = """\
You are writing a real business email on behalf of a manufacturer.
This is NOT a template. Use their actual product details, origin story, and certifications.
Write as if you know their business personally.
The email should read like it was written by a senior export manager who has sold to
{target_country} distributors before.
Write the email body in {target_language}. Subject lines can be in {target_language}.
Be direct, specific, credible. Avoid generic phrases like "I would like to introduce" or
"We are pleased to present". Start with a value statement.
"""

_SECTION5_TOOL = {
    "name": "submit_first_contact_kit",
    "description": "Submit the complete first contact kit for the manufacturer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "email_subject_variants": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Three subject line variants in target language",
            },
            "email_body": {
                "type": "string",
                "description": "Full email body in target language — NOT a template",
            },
            "follow_up_day3": {
                "type": "string",
                "description": "Follow-up message for day 3 in target language",
            },
            "follow_up_day7": {
                "type": "string",
                "description": "Follow-up message for day 7 in target language",
            },
            "follow_up_day14": {
                "type": "string",
                "description": "Follow-up message for day 14 in target language",
            },
            "objection_handling": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "objection": {"type": "string"},
                        "response": {"type": "string"},
                    },
                    "required": ["objection", "response"],
                },
                "description": "2-3 common objections with specific responses",
            },
            "origin_positioning": {
                "type": "string",
                "description": "2 sentences positioning the origin country as an asset",
            },
            "attachments_to_include": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of documents to attach with the first email",
            },
        },
        "required": [
            "email_subject_variants", "email_body",
            "follow_up_day3", "follow_up_day7", "follow_up_day14",
            "objection_handling", "origin_positioning", "attachments_to_include",
        ],
    },
}


def _build_section5_prompt(
    manufacturer: ManufacturerInput,
    warm_buyers: list[BuyerOutput],
    demand: DemandOutput,
    deep_research: DeepResearchOutput,
    target_language: str,
    target_country: str,
    origin_country: str,
) -> str:
    warm_buyer_summaries = []
    for b in warm_buyers[:3]:
        warm_buyer_summaries.append({
            "company": b.company_name,
            "city": b.city,
            "contact": b.contact_name,
            "title": b.contact_title,
            "signals": b.receptiveness_signals[:2],
            "score": b.receptiveness_score,
        })

    certifications_held = manufacturer.certifications or []

    lc = demand.landed_cost
    margin_str = f"{lc.margin:.1%} ({lc.margin_verdict})" if lc else "margin data unavailable"

    return json.dumps({
        "manufacturer": {
            "company": manufacturer.company or f"{origin_country} manufacturer",
            "origin_country": origin_country,
            "hs_code": manufacturer.hs_code,
            "unit_cost_eur": manufacturer.unit_cost_eur,
            "certifications_held": certifications_held,
            "capacity": manufacturer.capacity_units,
        },
        "target": {
            "country": target_country,
            "language": target_language,
        },
        "top_warm_buyers": warm_buyer_summaries,
        "market_context": {
            "import_value_usd": demand.import_value_usd,
            "margin": margin_str,
            "wholesale_mid_eur": (
                round((demand.wholesale_low_eur + demand.wholesale_high_eur) / 2, 0)
                if demand.wholesale_low_eur and demand.wholesale_high_eur else None
            ),
            "competitor_summary": demand.competitor_summary,
            "market_narrative_excerpt": (
                deep_research.market_narrative[:600] if deep_research.market_narrative else ""
            ),
        },
        "task": (
            f"Write a first contact email in {target_language} from this {origin_country} manufacturer "
            f"to a {target_country} furniture distributor. "
            "Use real product specifics — do NOT use placeholders like [Your Company Name]. "
            "The email should be 150–200 words, direct, and end with a single clear ask. "
            "Write subject lines in the target language."
        ),
    }, ensure_ascii=False)


# ─────────────────────────────────────────
# Section 6: 90-day action plan
# ─────────────────────────────────────────

_SECTION6_SYSTEM = """\
You are a practical export advisor writing a week-by-week action plan for a first-time exporter.
Every item must have a SPECIFIC action — not a vague goal.
Name actual companies, phone numbers from the compliance data, realistic deadlines.
Owner should be "CEO/owner", "you", or a specific role. Never use "TBD".
"""

_SECTION6_TOOL = {
    "name": "submit_action_plan",
    "description": "Submit the 90-day week-by-week action plan.",
    "input_schema": {
        "type": "object",
        "properties": {
            "weeks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "week_number": {"type": "integer"},
                        "title": {"type": "string"},
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "owner": {"type": "string"},
                                    "action": {"type": "string"},
                                    "definition_of_done": {"type": "string"},
                                    "cash_note": {"type": ["string", "null"]},
                                },
                                "required": ["owner", "action", "definition_of_done"],
                            },
                        },
                    },
                    "required": ["week_number", "title", "tasks"],
                },
            },
            "go_no_go_checkpoint": {
                "type": "string",
                "description": "What to evaluate at day 30 to decide whether to continue",
            },
            "trade_fair_recommendation": {
                "type": ["string", "null"],
                "description": "Specific trade fair to attend if outreach fails — name, location, month",
            },
        },
        "required": ["weeks", "go_no_go_checkpoint"],
    },
}


def _build_section6_prompt(
    manufacturer: ManufacturerInput,
    compliance: ComplianceOutput,
    buyer_list: BuyerList,
    deep_research: DeepResearchOutput,
    working_capital: WorkingCapitalEstimate,
    sector_config: dict,
    origin_country: str,
    target_country: str,
) -> str:
    critical_item = next((i for i in compliance.items if i.critical), None)
    trade_fairs = sector_config.get("trade_fairs", [])
    target_fair = next(
        (f for f in trade_fairs if f.get("country") == manufacturer.target_iso2),
        trade_fairs[0] if trade_fairs else None,
    )

    warm_buyer_contacts = [
        {
            "company": b.company_name,
            "contact": b.contact_name,
            "email": b.contact_email,
        }
        for b in buyer_list.warm[:3]
    ]

    return json.dumps({
        "manufacturer": {
            "origin_country": origin_country,
            "hs_code": manufacturer.hs_code,
            "certifications_held": manufacturer.certifications,
        },
        "target_country": target_country,
        "working_capital": {
            "total_needed_eur": working_capital.total_needed_eur,
            "days_to_revenue": working_capital.days_to_revenue,
            "compliance_cost_eur": working_capital.compliance_cost_eur,
            "goods_cost_eur": working_capital.goods_cost_eur,
        },
        "critical_compliance_item": {
            "name": critical_item.cert_name if critical_item else None,
            "lead_time_weeks": f"{critical_item.lead_time_min}–{critical_item.lead_time_max}" if critical_item else None,
            "providers": critical_item.providers[:2] if critical_item else [],
            "cost_eur": f"€{critical_item.cost_low_eur:,}–€{critical_item.cost_high_eur:,}" if critical_item else None,
        },
        "all_compliance_items": [
            {
                "name": i.cert_name,
                "lead_time": f"{i.lead_time_min}–{i.lead_time_max} weeks",
                "provider": i.providers[0] if i.providers else None,
                "cost": f"€{i.cost_low_eur:,}–€{i.cost_high_eur:,}",
            }
            for i in compliance.items
        ],
        "warm_buyers": warm_buyer_contacts,
        "trade_fair": target_fair,
        "task": (
            "Write a 90-day week-by-week action plan covering: "
            "Week 1-2: first buyer outreach + start compliance process; "
            "Week 3-4: follow-ups + book certification appointments; "
            "Week 5-8: compliance in progress + second outreach wave; "
            "Week 9-13: follow through on certifications + day-30 go/no-go review. "
            "Be specific about WHO does WHAT by WHEN. Name providers, phone numbers, email addresses where known."
        ),
    }, ensure_ascii=False)


# ─────────────────────────────────────────
# Section 7: Risk flags
# ─────────────────────────────────────────

_SECTION7_SYSTEM = """\
You are a risk analyst writing specific risk flags for a Balkan manufacturer entering a European market.
These must be specific to THIS manufacturer × THIS market combination — NOT generic warnings.
Reference their HS code, origin country, target market, and compliance requirements explicitly.
Each risk title should be a one-line summary of the specific threat.
"""

_SECTION7_TOOL = {
    "name": "submit_risk_flags",
    "description": "Submit 3-4 specific risk flags for this manufacturer × market pair.",
    "input_schema": {
        "type": "object",
        "properties": {
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "severity": {"type": "string", "enum": ["high", "medium"]},
                    },
                    "required": ["title", "description", "severity"],
                },
                "minItems": 3,
                "maxItems": 4,
            },
            "alternative_market": {
                "type": ["string", "null"],
                "description": "2 sentences on the best alternative market if this one fails",
            },
        },
        "required": ["risks"],
    },
}


def _build_section7_prompt(
    manufacturer: ManufacturerInput,
    demand: DemandOutput,
    compliance: ComplianceOutput,
    buyer_list: BuyerList,
    deep_research: DeepResearchOutput,
    origin_country: str,
    target_country: str,
) -> str:
    lc = demand.landed_cost
    critical = next((i for i in compliance.items if i.critical), None)

    return json.dumps({
        "manufacturer": {
            "origin_country": origin_country,
            "hs_code": manufacturer.hs_code,
            "unit_cost_eur": manufacturer.unit_cost_eur,
            "certifications_held": manufacturer.certifications,
        },
        "target_country": target_country,
        "market_data": {
            "top_suppliers": [s.model_dump() for s in demand.top_suppliers[:3]],
            "margin": lc.margin if lc else None,
            "margin_verdict": lc.margin_verdict if lc else None,
            "fx_volatility_90d": demand.fx_volatility_90d,
            "trade_agreement": demand.trade_agreement,
        },
        "compliance_risk": {
            "critical_item": critical.cert_name if critical else None,
            "critical_lead_time_weeks": f"{critical.lead_time_min}–{critical.lead_time_max}" if critical else None,
            "total_compliance_cost_eur": compliance.total_cost_high_eur,
        },
        "buyer_data": {
            "warm_count": len(buyer_list.warm),
            "cold_count": len(buyer_list.cold),
        },
        "deep_research_excerpt": deep_research.market_narrative[:400] if deep_research.market_narrative else "",
        "task": (
            f"Write 3-4 specific risk flags for this {origin_country} manufacturer "
            f"selling HS {manufacturer.hs_code} into {target_country}. "
            "Include: the most likely compliance deal-killer, main competitive threat, "
            "any FX or working capital risk, and one 'what if this fails' alternative market. "
            "Risks must reference specific details from the data — no generic warnings."
        ),
    }, ensure_ascii=False)


# ─────────────────────────────────────────
# Claude calls
# ─────────────────────────────────────────

def _call_claude_with_tool(
    system: str,
    prompt: str,
    tool: dict,
    max_tokens: int = 2000,
) -> Optional[dict]:
    """Call Claude Sonnet 4.6 with tool_use to enforce JSON schema output."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        return None

    client = Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return block.input
    except Exception as e:
        print(f"[Worker 5] Claude tool call failed ({tool['name']}): {e}")

    return None


def _call_gemini_synthesis(
    system: str,
    prompt_data: dict,
    task_name: str,
    response_schema: dict,
) -> Optional[dict]:
    """Gemini fallback for synthesis sections."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("#"):
        return None

    full_prompt = json.dumps({**prompt_data, "_system": system}, ensure_ascii=False)
    models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 3000,
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
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
            result = json.loads(content) if isinstance(content, str) else content
            print(f"[Worker 5] Gemini fallback used for {task_name} ({model})")
            return result
        except Exception as e:
            print(f"[Worker 5] Gemini {model} error for {task_name}: {e}")
            continue

    return None


# ─────────────────────────────────────────
# Placeholder generators (all LLMs failed)
# ─────────────────────────────────────────

def _placeholder_section5(manufacturer: ManufacturerInput, target_country: str, target_language: str) -> dict:
    company = manufacturer.company or "our company"
    return {
        "email_subject_variants": [
            f"Solid oak furniture from {_ORIGIN_NAMES.get(manufacturer.origin_iso2, 'Kosovo')} — wholesale enquiry",
            f"New supplier for {target_country} distributors — HS {manufacturer.hs_code}",
            f"Direct from manufacturer: solid wood furniture at €{manufacturer.unit_cost_eur}/unit",
        ],
        "email_body": (
            f"Dear [Purchasing Manager],\n\n"
            f"We manufacture solid oak furniture at {company} in {_ORIGIN_NAMES.get(manufacturer.origin_iso2, 'Kosovo')}. "
            f"Our unit cost is €{manufacturer.unit_cost_eur} and we have capacity for {manufacturer.capacity_units} per month. "
            f"We are FSC-certifiable and have been producing for EU markets.\n\n"
            "I would like to arrange a brief call to discuss whether there is a fit with your range.\n\n"
            "Best regards"
        ),
        "follow_up_day3": "Following up on my email from 3 days ago — happy to send product photos and a spec sheet.",
        "follow_up_day7": "One more follow-up — if you are not the right contact for new supplier enquiries, could you point me to the right person?",
        "follow_up_day14": "Final follow-up for now. I will reach out again in 60 days. Our catalogue is attached.",
        "objection_handling": [
            {"objection": "We already have suppliers", "response": "We are not asking you to switch — we are asking for a backup source."},
            {"objection": "We do not know Kosovo manufacturers", "response": "Kosovo is FSC-certifiable, within 5 days by road, and 30–40% cheaper than Austrian domestic."},
        ],
        "origin_positioning": (
            f"{_ORIGIN_NAMES.get(manufacturer.origin_iso2, 'Kosovo')} oak — proximity to EU, lower cost than Austrian domestic, "
            "FSC-certifiable from certified forests — positions you as a credible European supplier, not a distant importer."
        ),
        "attachments_to_include": ["Product photos", "Technical specification sheet", "Certifications held"],
    }


def _placeholder_section6(compliance: ComplianceOutput, buyer_list: BuyerList, working_capital: WorkingCapitalEstimate) -> dict:
    critical = next((i for i in compliance.items if i.critical), None)
    warm_emails = [b.contact_email or b.company_name for b in buyer_list.warm[:3]]

    return {
        "weeks": [
            {
                "week_number": 1,
                "title": "First contact + start compliance",
                "tasks": [
                    {
                        "owner": "CEO/owner",
                        "action": f"Email warm buyers: {', '.join(warm_emails) if warm_emails else 'buyers from shortlist'}",
                        "definition_of_done": "Emails sent, delivery confirmed",
                        "cash_note": None,
                    },
                    {
                        "owner": "CEO/owner",
                        "action": f"Call {critical.providers[0] if critical and critical.providers else 'certification body'} about {critical.cert_name if critical else 'FSC certification'} pre-audit",
                        "definition_of_done": "Pre-audit call booked",
                        "cash_note": f"Budget €{critical.cost_low_eur:,} for certification" if critical else None,
                    },
                ],
            },
            {
                "week_number": 2,
                "title": "Follow-up + book certification",
                "tasks": [
                    {
                        "owner": "CEO/owner",
                        "action": "Follow up with buyers who have not replied — adjust subject line",
                        "definition_of_done": "Follow-up sent",
                        "cash_note": None,
                    },
                ],
            },
            {
                "week_number": 4,
                "title": "Day-30 go/no-go review",
                "tasks": [
                    {
                        "owner": "CEO/owner",
                        "action": "Review buyer responses — if no warm reply, move to cold list",
                        "definition_of_done": "Decision made on continuing with warm list vs cold list",
                        "cash_note": None,
                    },
                ],
            },
        ],
        "go_no_go_checkpoint": (
            "By day 30: if no reply from warm buyers, switch to cold list and adjust subject line. "
            "If still no response by day 45, consider attending the sector trade fair for in-person meetings."
        ),
        "trade_fair_recommendation": None,
    }


def _placeholder_section7(
    manufacturer: ManufacturerInput,
    demand: DemandOutput,
    compliance: ComplianceOutput,
    origin_country: str,
    target_country: str,
) -> dict:
    critical = next((i for i in compliance.items if i.critical), None)
    lc = demand.landed_cost
    risks = [
        {
            "title": f"Compliance delay: {critical.cert_name}" if critical else "Certification timeline risk",
            "description": (
                f"{critical.cert_name} takes {critical.lead_time_min}–{critical.lead_time_max} weeks and costs "
                f"€{critical.cost_low_eur:,}–€{critical.cost_high_eur:,}. Starting late will block your first order."
                if critical else "Certifications must be started before buyer negotiations to avoid delays."
            ),
            "severity": "high",
        },
        {
            "title": f"Price pressure from established suppliers in {target_country}",
            "description": (
                f"Top suppliers ({', '.join(s.country for s in demand.top_suppliers[:2])} "
                "if top_suppliers else 'existing EU suppliers') "
                "have incumbent relationships. Compete on FSC, proximity, and personalised service — not price."
            ),
            "severity": "medium",
        },
        {
            "title": "Working capital gap before first payment",
            "description": (
                f"You will invest in goods + compliance before receiving any payment. "
                f"Margin of {lc.margin:.1%} is {lc.margin_verdict} — ensure cash runway covers 80-day gap."
                if lc else "Ensure adequate cash flow to cover compliance and first-order costs before payment arrives."
            ),
            "severity": "medium",
        },
    ]
    return {
        "risks": risks,
        "alternative_market": (
            f"If {target_country} does not respond within 60 days, consider Italy next: "
            "shorter freight distance from WB6, higher volume furniture import market, and "
            "cultural familiarity with Southern European sourcing."
        ),
    }


# ─────────────────────────────────────────
# Report markdown assembly
# ─────────────────────────────────────────

def _fmt_eur(val: Optional[float]) -> str:
    return f"€{val:,.0f}" if val is not None else "N/A"


def _fmt_pct(val: Optional[float]) -> str:
    return f"{val:.1%}" if val is not None else "N/A"


def _assemble_report_markdown(
    manufacturer: ManufacturerInput,
    demand: DemandOutput,
    compliance: ComplianceOutput,
    buyer_list: BuyerList,
    deep_research: DeepResearchOutput,
    working_capital: WorkingCapitalEstimate,
    section5: dict,
    section6: dict,
    section7: dict,
    tier: str,
    origin_country: str,
    target_country: str,
) -> str:
    lines: list[str] = []

    # Header
    lines.append(f"# Quorint Export Intelligence Report")
    lines.append(f"**{origin_country} → {target_country} | HS {manufacturer.hs_code}**")
    lines.append("")

    # ── Section 1: Market Demand Snapshot ──────────────────────────────────
    lines.append("## Section 1: Market Demand Snapshot")
    lines.append("")
    if demand.import_value_usd:
        lines.append(f"**Import value (latest year):** ${demand.import_value_usd:,}")
    if demand.cagr_5yr is not None:
        trend = "growing" if demand.cagr_5yr > 0 else "declining"
        lines.append(f"**5-year trend:** {trend} ({demand.cagr_5yr:.1%} CAGR)")
    if demand.top_suppliers:
        top = ", ".join(f"{s.country} ({s.share:.0%})" for s in demand.top_suppliers[:5])
        lines.append(f"**Top suppliers:** {top}")
    if demand.trade_agreement:
        lines.append(f"**Trade agreement:** {demand.trade_agreement}")
    if demand.tariff_preferential is not None:
        lines.append(f"**Preferential tariff:** {demand.tariff_preferential:.1%}")
    elif demand.tariff_mfn is not None:
        lines.append(f"**MFN tariff:** {demand.tariff_mfn:.1%}")
    lines.append("")
    if demand.demand_narrative:
        lines.append(demand.demand_narrative)
    if demand.one_sentence_verdict:
        lines.append(f"\n**Verdict:** {demand.one_sentence_verdict}")
    lines.append("")

    # ── Section 2: Price Reality Check ─────────────────────────────────────
    lines.append("## Section 2: Price Reality Check")
    lines.append("")
    if demand.retail_median_eur:
        lines.append(f"**Retail prices (EUR):** p25 {_fmt_eur(demand.retail_p25_eur)} | "
                     f"median {_fmt_eur(demand.retail_median_eur)} | p75 {_fmt_eur(demand.retail_p75_eur)}")
    if demand.wholesale_low_eur and demand.wholesale_high_eur:
        lines.append(f"**Wholesale range:** {_fmt_eur(demand.wholesale_low_eur)} – {_fmt_eur(demand.wholesale_high_eur)}")
    lines.append("")

    lc = demand.landed_cost
    if lc:
        verdict_marker = {"viable": "✅", "tight": "⚠️", "not_viable": "❌"}.get(lc.margin_verdict, "")
        lines.append("**Landed cost breakdown:**")
        lines.append(f"| Item | Per unit |")
        lines.append(f"|------|----------|")
        lines.append(f"| Unit production cost | {_fmt_eur(lc.unit_cost_eur)} |")
        lines.append(f"| Road freight ({lc.units_per_truck} units/truck) | {_fmt_eur(lc.freight_per_unit_eur)} |")
        lines.append(f"| Customs & docs | {_fmt_eur(lc.customs_per_unit_eur)} |")
        lines.append(f"| Insurance | {_fmt_eur(lc.insurance_per_unit_eur)} |")
        lines.append(f"| **DAP (landed cost)** | **{_fmt_eur(lc.dap_per_unit_eur)}** |")
        lines.append(f"| Wholesale mid-point | {_fmt_eur(lc.wholesale_mid_eur)} |")
        lines.append(f"| **Margin** | **{lc.margin:.1%} {verdict_marker} ({lc.margin_verdict.upper()})** |")
        lines.append("")
        if lc.margin_verdict == "not_viable":
            lines.append("⚠️ **Margin is below viable threshold.** Consider an adjacent market before proceeding.")
    else:
        lines.append("_Landed cost unavailable — missing retail price or freight data._")
    lines.append("")

    if demand.competitor_summary:
        lines.append("**Competitor landscape:**")
        lines.append(demand.competitor_summary)
        lines.append("")

    # ── Section 3: Compliance Map ────────────────────────────────────────────
    lines.append("## Section 3: Compliance Map")
    lines.append("")
    lines.append(f"**Total compliance investment:** "
                 f"€{compliance.total_cost_low_eur:,} – €{compliance.total_cost_high_eur:,}")
    lines.append("")

    for item in compliance.items:
        critical_marker = " 🔴 **CRITICAL**" if item.critical else ""
        type_label = {"mandatory": "Mandatory", "commercial_expected": "Commercially expected", "recommended": "Recommended"}.get(item.cert_type, item.cert_type)
        lines.append(f"### {item.cert_name}{critical_marker}")
        lines.append(f"- **Type:** {type_label}")
        lines.append(f"- **Cost:** €{item.cost_low_eur:,} – €{item.cost_high_eur:,}")
        lines.append(f"- **Lead time:** {item.lead_time_min}–{item.lead_time_max} weeks")
        if item.providers:
            lines.append(f"- **Providers:** {'; '.join(item.providers[:3])}")
        if item.note:
            lines.append(f"- **Note:** {item.note}")
        lines.append("")

    # ── Section 4: Buyer Shortlist ───────────────────────────────────────────
    lines.append("## Section 4: Buyer Shortlist")
    lines.append("")

    all_buyers = buyer_list.warm + buyer_list.cold
    if not all_buyers:
        lines.append("_No buyers found for this market segment._")
    else:
        # Warm buyers
        if buyer_list.warm:
            lines.append("### Warm Buyers — Contact This Week")
            lines.append("")
            for b in buyer_list.warm:
                lines.append(f"#### {b.company_name}")
                if b.city:
                    lines.append(f"**Location:** {b.city}, {b.country_iso2}")
                if b.buyer_type:
                    lines.append(f"**Type:** {b.buyer_type}")
                if b.contact_name:
                    contact_line = b.contact_name
                    if b.contact_title:
                        contact_line += f", {b.contact_title}"
                    lines.append(f"**Contact:** {contact_line}")
                if b.contact_email:
                    lines.append(f"**Email:** {b.contact_email}")
                if b.linkedin_url:
                    lines.append(f"**LinkedIn:** {b.linkedin_url}")
                if tier == "full":
                    lines.append(f"**Receptiveness score:** {b.receptiveness_score}/100")
                    if b.receptiveness_signals:
                        lines.append("**Signals:**")
                        for sig in b.receptiveness_signals:
                            lines.append(f"  - {sig}")
                lines.append("")

        # Cold buyers (only in full tier)
        if buyer_list.cold and tier == "full":
            lines.append("### Cold Buyers — 90-Day Nurture List")
            lines.append("")
            for b in buyer_list.cold[:10]:
                lines.append(f"- **{b.company_name}** ({b.city or b.country_iso2})"
                             + (f" — {b.contact_name}" if b.contact_name else "")
                             + f" [score: {b.receptiveness_score}]")
            lines.append("")

    # ── Section 5: First Contact Kit ─────────────────────────────────────────
    lines.append("## Section 5: First Contact Kit")
    lines.append("")

    if section5.get("email_subject_variants"):
        lines.append("**Subject line options:**")
        for i, subj in enumerate(section5["email_subject_variants"], 1):
            lines.append(f"{i}. {subj}")
        lines.append("")

    if section5.get("email_body"):
        lines.append("**Email (send this week):**")
        lines.append("")
        lines.append("---")
        lines.append(section5["email_body"])
        lines.append("---")
        lines.append("")

    if tier == "full":
        if section5.get("follow_up_day3"):
            lines.append(f"**Day 3 follow-up:** {section5['follow_up_day3']}")
        if section5.get("follow_up_day7"):
            lines.append(f"**Day 7 follow-up:** {section5['follow_up_day7']}")
        if section5.get("follow_up_day14"):
            lines.append(f"**Day 14 follow-up:** {section5['follow_up_day14']}")
        lines.append("")

        if section5.get("origin_positioning"):
            lines.append(f"**Positioning your origin:** {section5['origin_positioning']}")
            lines.append("")

        if section5.get("attachments_to_include"):
            lines.append("**Attach to first email:**")
            for att in section5["attachments_to_include"]:
                lines.append(f"- {att}")
            lines.append("")

        if section5.get("objection_handling"):
            lines.append("**Common objections:**")
            for oh in section5["objection_handling"]:
                lines.append(f"- **\"{oh['objection']}\"** → {oh['response']}")
            lines.append("")

    # ── Section 6: 90-Day Action Plan ─────────────────────────────────────────
    lines.append("## Section 6: 90-Day Action Plan")
    lines.append("")

    lines.append(f"> {working_capital.plain_english}")
    lines.append("")

    for week in section6.get("weeks", []):
        lines.append(f"### Week {week['week_number']}: {week['title']}")
        for task in week.get("tasks", []):
            lines.append(f"- **{task['owner']}:** {task['action']}")
            lines.append(f"  _Done when:_ {task['definition_of_done']}")
            if task.get("cash_note"):
                lines.append(f"  💰 {task['cash_note']}")
        lines.append("")

    if section6.get("go_no_go_checkpoint"):
        lines.append(f"**Day 30 checkpoint:** {section6['go_no_go_checkpoint']}")
        lines.append("")

    if section6.get("trade_fair_recommendation"):
        lines.append(f"**Trade fair option:** {section6['trade_fair_recommendation']}")
        lines.append("")

    # ── Section 7: Risk Flags ──────────────────────────────────────────────────
    lines.append("## Section 7: Risk Flags")
    lines.append("")

    for risk in section7.get("risks", []):
        severity_icon = "🔴" if risk["severity"] == "high" else "🟡"
        lines.append(f"### {severity_icon} {risk['title']}")
        lines.append(risk["description"])
        lines.append("")

    if section7.get("alternative_market"):
        lines.append(f"**Alternative market:** {section7['alternative_market']}")
        lines.append("")

    # ── Deep Research Appendix (full tier only) ────────────────────────────────
    if tier == "full" and deep_research.market_narrative:
        lines.append("## Appendix: Market Intelligence")
        lines.append("")
        lines.append(deep_research.market_narrative)
        lines.append("")
        if deep_research.sources:
            lines.append("**Sources:**")
            for src in deep_research.sources[:10]:
                lines.append(f"- {src}")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Generated by Quorint — quorint.com*")

    return "\n".join(lines)


# ─────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────

@observe(name="worker_synthesis")
def run_synthesis(
    manufacturer: ManufacturerInput,
    demand: DemandOutput,
    compliance: ComplianceOutput,
    buyer_list: BuyerList,
    deep_research: DeepResearchOutput,
    tier: str = "full",
) -> ReportSynthesis:
    """
    Worker 5: assembles all worker outputs into the complete report.

    1. Calculates working capital (deterministic Python)
    2. Calls Claude for Section 5 (first contact email in target language)
    3. Calls Claude for Section 6 (90-day action plan)
    4. Calls Claude for Section 7 (risk flags)
    5. Assembles complete report markdown

    Canonical test: hs_code="940360", origin="XK", target="AT", unit_cost=200.0
    """
    origin_country = _ORIGIN_NAMES.get(manufacturer.origin_iso2, manufacturer.origin_iso2)
    target_country = _COUNTRY_NAMES.get(manufacturer.target_iso2, manufacturer.target_iso2)
    target_language = _TARGET_LANGUAGES.get(manufacturer.target_iso2, "English")

    print(f"[Worker 5] Starting synthesis for HS {manufacturer.hs_code} {manufacturer.origin_iso2}→{manufacturer.target_iso2}")

    # Step 1: Working capital (deterministic)
    sector_config = load_sector_config(manufacturer.hs_code)
    working_capital = calculate_working_capital(
        unit_cost=manufacturer.unit_cost_eur,
        sector_config=sector_config,
        compliance_output=compliance,
    )

    # Step 2: Section 5 — First contact kit (Claude Sonnet 4.6)
    section5_system = _SECTION5_SYSTEM.format(
        target_country=target_country,
        target_language=target_language,
    )
    section5_prompt = _build_section5_prompt(
        manufacturer=manufacturer,
        warm_buyers=buyer_list.warm,
        demand=demand,
        deep_research=deep_research,
        target_language=target_language,
        target_country=target_country,
        origin_country=origin_country,
    )

    section5 = _call_claude_with_tool(
        system=section5_system,
        prompt=section5_prompt,
        tool=_SECTION5_TOOL,
        max_tokens=2500,
    )
    if not section5:
        print("[Worker 5] Claude Section 5 failed — using placeholder")
        section5 = _placeholder_section5(manufacturer, target_country, target_language)

    # Step 3: Section 6 — 90-day action plan (Claude Sonnet 4.6)
    section6_prompt = _build_section6_prompt(
        manufacturer=manufacturer,
        compliance=compliance,
        buyer_list=buyer_list,
        deep_research=deep_research,
        working_capital=working_capital,
        sector_config=sector_config,
        origin_country=origin_country,
        target_country=target_country,
    )
    section6 = _call_claude_with_tool(
        system=_SECTION6_SYSTEM,
        prompt=section6_prompt,
        tool=_SECTION6_TOOL,
        max_tokens=3000,
    )
    if not section6:
        print("[Worker 5] Claude Section 6 failed — using placeholder")
        section6 = _placeholder_section6(compliance, buyer_list, working_capital)

    # Step 4: Section 7 — Risk flags (Claude Sonnet 4.6)
    section7_prompt = _build_section7_prompt(
        manufacturer=manufacturer,
        demand=demand,
        compliance=compliance,
        buyer_list=buyer_list,
        deep_research=deep_research,
        origin_country=origin_country,
        target_country=target_country,
    )
    section7 = _call_claude_with_tool(
        system=_SECTION7_SYSTEM,
        prompt=section7_prompt,
        tool=_SECTION7_TOOL,
        max_tokens=1500,
    )
    if not section7:
        print("[Worker 5] Claude Section 7 failed — using placeholder")
        section7 = _placeholder_section7(manufacturer, demand, compliance, origin_country, target_country)

    # Step 5: Assemble complete report markdown
    full_markdown = _assemble_report_markdown(
        manufacturer=manufacturer,
        demand=demand,
        compliance=compliance,
        buyer_list=buyer_list,
        deep_research=deep_research,
        working_capital=working_capital,
        section5=section5,
        section6=section6,
        section7=section7,
        tier=tier,
        origin_country=origin_country,
        target_country=target_country,
    )

    # Build action plan markdown snippet (for ReportSynthesis.action_plan_markdown)
    action_plan_lines = []
    for week in section6.get("weeks", []):
        action_plan_lines.append(f"**Week {week['week_number']}: {week['title']}**")
        for task in week.get("tasks", []):
            action_plan_lines.append(f"- {task['action']}")
    action_plan_md = "\n".join(action_plan_lines)

    # Build risk flags markdown snippet
    risk_lines = []
    for risk in section7.get("risks", []):
        risk_lines.append(f"- **{risk['title']}** ({risk['severity']}): {risk['description']}")
    risk_md = "\n".join(risk_lines)

    follow_up = {
        "day3": section5.get("follow_up_day3", ""),
        "day7": section5.get("follow_up_day7", ""),
        "day14": section5.get("follow_up_day14", ""),
    }

    return ReportSynthesis(
        first_contact_email=section5.get("email_body", ""),
        first_contact_subject_lines=section5.get("email_subject_variants", []),
        follow_up_sequence=follow_up,
        origin_positioning=section5.get("origin_positioning", ""),
        action_plan_markdown=action_plan_md,
        risk_flags_markdown=risk_md,
        working_capital=working_capital,
        full_report_markdown=full_markdown,
    )
