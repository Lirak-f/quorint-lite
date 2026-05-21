"""Receptiveness scoring engine for buyer shortlisting."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from models import ManufacturerInput


def _fuzzy_match(name: str, candidates: list[str], threshold: float = 0.72) -> bool:
    """Return True if name fuzzy-matches any candidate above threshold."""
    name_lower = name.lower()
    for candidate in candidates:
        ratio = SequenceMatcher(None, name_lower, candidate.lower()).ratio()
        if ratio >= threshold:
            return True
    return False


def score_buyer(
    buyer: dict[str, Any],
    manufacturer: ManufacturerInput,
    comtrade_mirror: dict[str, Any],
    perplexity_signals: dict[str, Any],
    trade_fairs: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    """
    Score a buyer's receptiveness on 5 signals.
    Returns (score: int 0–100, signals: list[str] describing what fired).

    Signal weights:
      1. Import diversification  — 35 pts max
      2. Active sourcing         — 30 pts max
      3. Growth trajectory       — 15 pts max
      4. Trade fair activity     — 10 pts max
      5. Decision-maker access   — 10 pts max
    """
    score = 0
    signals: list[str] = []

    buyer_country = buyer.get("country_iso2", "")
    company_name = buyer.get("company_name", "")

    # ─── Signal 1: Import diversification (35 pts max) ─────────────────────
    # comtrade_mirror structure: {country_iso2: {origin_iso2: {value, trend}}}
    country_import_data = comtrade_mirror.get(buyer_country, {})
    origin_data = country_import_data.get(manufacturer.origin_iso2)

    if origin_data is None:
        # Buyer's country does not currently import from our origin — good signal
        score += 25
        signals.append(
            f"Import diversification: {buyer_country} does not currently import from "
            f"{manufacturer.origin_iso2} — no incumbent supplier relationship to displace."
        )

        # Check if any existing supplier's frequency dropped
        any_drop = any(
            v.get("trend") == "declining"
            for o, v in country_import_data.items()
            if isinstance(v, dict)
        )
        if any_drop:
            score += 10
            signals.append(
                "Import diversification+: Existing supplier import frequency declining — "
                "buyer may be actively seeking alternatives."
            )
    else:
        # Origin already exports to this country — incumbent exists
        score += 5
        signals.append(
            f"Import diversification: {buyer_country} already imports from {manufacturer.origin_iso2} "
            "— incumbent supplier exists, harder to displace."
        )
        # Still check for declining trend from existing suppliers
        if origin_data.get("trend") == "declining":
            score += 5
            signals.append(
                "Import diversification+: Imports from origin country trending down — "
                "buyer may be ready to switch suppliers."
            )

    # ─── Signal 2: Active sourcing (30 pts max) ────────────────────────────
    # perplexity_signals: {company_name: {job_posting: bool, sourcing_news: bool, summary: str}}
    buyer_signals = perplexity_signals.get(company_name, {})

    if buyer_signals.get("job_posting"):
        score += 20
        signals.append(
            "Active sourcing: Job posting for procurement/purchasing/sourcing found in last 90 days — "
            "actively hiring for supply chain roles."
        )

    if buyer_signals.get("sourcing_news"):
        score += 10
        signals.append(
            "Active sourcing: Recent news about supplier base expansion or new product sourcing."
        )

    # ─── Signal 3: Growth trajectory (15 pts max) ──────────────────────────
    revenue_trend = buyer.get("revenue_trend")  # "growing" | "flat" | "declining" | None
    if revenue_trend == "growing":
        score += 15
        signals.append("Growth trajectory: Company revenue trending up — growing companies need more product.")
    elif revenue_trend == "flat" or revenue_trend is None:
        score += 8
        # Neutral — no signal added, give baseline points for companies we have data on
    # declining → 0 pts, no signal

    # ─── Signal 4: Trade fair activity (10 pts max) ────────────────────────
    # Check if company appears in any upcoming trade fair exhibitor list
    fair_exhibitors: list[str] = []
    for fair in trade_fairs:
        fair_exhibitors.extend(fair.get("exhibitors", []))

    if fair_exhibitors and _fuzzy_match(company_name, fair_exhibitors):
        score += 10
        matching_fair = next(
            (f.get("name", "trade fair") for f in trade_fairs if _fuzzy_match(company_name, f.get("exhibitors", []))),
            "upcoming trade fair",
        )
        signals.append(
            f"Trade fair activity: Company is exhibiting at {matching_fair} — "
            "in market-development mode, not cost-cutting."
        )

    # ─── Signal 5: Decision-maker accessibility (10 pts max) ───────────────
    contact_name = buyer.get("contact_name")
    contact_email = buyer.get("contact_email")

    if contact_name and contact_email:
        score += 10
        signals.append(
            f"Decision-maker accessible: Named contact ({contact_name}) with verified email — "
            "direct outreach possible."
        )
    elif contact_name:
        score += 5
        signals.append(
            f"Decision-maker partially accessible: Named contact ({contact_name}) but no verified email — "
            "LinkedIn outreach required."
        )
    # No contact → 0 pts, no signal

    # Cap at 100
    score = min(score, 100)

    return score, signals


def assign_tier(score: int) -> str:
    """Assign buyer tier from receptiveness score."""
    if score >= 70:
        return "warm"
    if score >= 40:
        return "cold"
    return "skip"
