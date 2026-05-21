"""Deterministic working capital estimator — no LLM involved."""

from __future__ import annotations

from models import ComplianceOutput, WorkingCapitalEstimate


def calculate_working_capital(
    unit_cost: float,
    sector_config: dict,
    compliance_output: ComplianceOutput,
) -> WorkingCapitalEstimate:
    """
    Calculate working capital needed before first export order.

    All math is deterministic — no LLM.
    Formula matches QUORINT_CONTEXT.md Section 6 spec exactly.
    """
    typical_first_order_units: int = sector_config.get("typical_first_order_units", 60)
    goods_cost = unit_cost * typical_first_order_units

    # Sum cost_low_eur for all items that apply (default: all items apply)
    compliance_cost = sum(
        item.cost_low_eur
        for item in compliance_output.items
        if item.applies
    )

    sample_shipping: float = float(sector_config.get("sample_shipping_cost_eur", 800))
    buffer = goods_cost * 0.15
    total_needed = goods_cost + compliance_cost + sample_shipping + buffer

    # 35 days lead time + 45 days payment terms midpoint (30–60 day range)
    days_to_revenue = 35 + 45

    plain_english = (
        f"Have at least €{round(total_needed):,} liquid before you send the first email. "
        f"First revenue arrives approximately {days_to_revenue} days after outreach begins."
    )

    return WorkingCapitalEstimate(
        goods_cost_eur=round(goods_cost),
        compliance_cost_eur=round(compliance_cost),
        sample_shipping_eur=sample_shipping,
        buffer_eur=round(buffer),
        total_needed_eur=round(total_needed),
        days_to_revenue=days_to_revenue,
        plain_english=plain_english,
    )
