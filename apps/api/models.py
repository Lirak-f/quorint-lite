"""Pydantic models for all worker outputs and database tables."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────
# Input models
# ─────────────────────────────────────────

class ManufacturerInput(BaseModel):
    hs_code: str = Field(..., description="4 or 6-digit HS code — entered by user, never AI-mapped")
    origin_iso2: Literal["XK", "AL", "RS", "BA", "MK", "ME"]
    target_iso2: str = Field(..., min_length=2, max_length=2)
    unit_cost_eur: float = Field(..., gt=0)
    certifications: list[str] = Field(default_factory=list)
    capacity_units: Literal["<100/mo", "100-500/mo", "500+/mo"] = "<100/mo"
    tier: Literal["starter", "full"] = "full"
    company: Optional[str] = None
    product_name: Optional[str] = None
    product_desc: Optional[str] = None
    # Product profile fields (Step 1b) — all optional for backward compat
    product_phrase: Optional[str] = None          # short specific phrase, e.g. "solid oak dining tables"
    end_buyer_type: Optional[str] = None          # wholesale|retail|oem|hospitality|institutional
    price_tier: Optional[str] = None             # value|mid|premium
    packaging_format: Optional[list[str]] = None  # bulk|wholesale_packs|retail_ready|private_label
    material_subtype: Optional[str] = None        # sector-specific, e.g. solid_wood|engineered_wood
    processing_level: Optional[str] = None        # sector-specific for metals: raw|fabricated|machined|assembled


class ReportJob(BaseModel):
    report_id: uuid.UUID
    manufacturer_input: ManufacturerInput
    is_test: bool = False


# ─────────────────────────────────────────
# Worker 1 — Market demand + pricing
# ─────────────────────────────────────────

class TopSupplier(BaseModel):
    country: str
    share: float
    trend: Optional[str] = None


class LandedCostBreakdown(BaseModel):
    unit_cost_eur: float
    freight_per_unit_eur: float
    customs_per_unit_eur: float
    insurance_per_unit_eur: float
    dap_per_unit_eur: float
    wholesale_mid_eur: float
    margin: float
    margin_verdict: Literal["viable", "tight", "not_viable"]
    units_per_truck: int


class DemandOutput(BaseModel):
    # Comtrade
    import_value_usd: Optional[int] = None
    cagr_5yr: Optional[float] = None
    top_suppliers: list[TopSupplier] = Field(default_factory=list)

    # WITS tariff
    tariff_mfn: Optional[float] = None
    tariff_preferential: Optional[float] = None
    trade_agreement: Optional[str] = None

    # OEC
    rca_score: Optional[float] = None

    # WDI
    gdp_usd: Optional[float] = None
    lpi_score: Optional[float] = None

    # Retail prices (ScraperAPI)
    retail_p25_eur: Optional[float] = None
    retail_median_eur: Optional[float] = None
    retail_p75_eur: Optional[float] = None
    wholesale_low_eur: Optional[float] = None
    wholesale_high_eur: Optional[float] = None

    # Freight (Supabase lookup)
    freight_low_eur: Optional[int] = None
    freight_high_eur: Optional[int] = None
    freight_mode: Optional[str] = None

    # FX (only for non-EUR origin)
    fx_volatility_90d: Optional[float] = None

    # Landed cost (deterministic Python)
    landed_cost: Optional[LandedCostBreakdown] = None

    # Claude synthesis
    competitor_summary: Optional[str] = None
    demand_narrative: Optional[str] = None
    one_sentence_verdict: Optional[str] = None


# ─────────────────────────────────────────
# Worker 2 — Compliance
# ─────────────────────────────────────────

class ComplianceItem(BaseModel):
    cert_id: str
    cert_name: str
    cert_type: Literal["mandatory", "commercial_expected", "recommended"]
    critical: bool = False
    cost_low_eur: int
    cost_high_eur: int
    lead_time_min: int
    lead_time_max: int
    providers: list[str]
    note: Optional[str] = None
    applies: bool = True  # set False to exclude from cost totals


class ComplianceOutput(BaseModel):
    items: list[ComplianceItem]
    total_cost_low_eur: int
    total_cost_high_eur: int
    critical_item_id: Optional[str] = None


# ─────────────────────────────────────────
# Worker 3 — Buyers
# ─────────────────────────────────────────

class BuyerOutput(BaseModel):
    company_name: str
    company_domain: Optional[str] = None
    city: Optional[str] = None
    country_iso2: str
    buyer_type: Optional[str] = None
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_email: Optional[str] = None
    linkedin_url: Optional[str] = None
    enrichment_source: Literal["apollo", "pdl", "perplexity"]
    receptiveness_score: int = Field(..., ge=0, le=100)
    receptiveness_signals: list[str] = Field(default_factory=list)
    tier: Literal["warm", "cold", "skip"]


class BuyerList(BaseModel):
    warm: list[BuyerOutput] = Field(default_factory=list)
    cold: list[BuyerOutput] = Field(default_factory=list)
    total_scored: int = 0


# ─────────────────────────────────────────
# Worker 4 — Deep research
# ─────────────────────────────────────────

class DeepResearchOutput(BaseModel):
    market_narrative: str
    sources: list[str] = Field(default_factory=list)
    additional_buyers: list[dict[str, Any]] = Field(default_factory=list)


# ─────────────────────────────────────────
# Worker 5 — Synthesis
# ─────────────────────────────────────────

class WorkingCapitalEstimate(BaseModel):
    goods_cost_eur: float
    compliance_cost_eur: float
    sample_shipping_eur: float
    buffer_eur: float
    total_needed_eur: float
    days_to_revenue: int
    plain_english: str = ""


class ReportSynthesis(BaseModel):
    first_contact_email: str
    first_contact_subject_lines: list[str]
    follow_up_sequence: dict[str, str]
    origin_positioning: str
    action_plan_markdown: str
    risk_flags_markdown: str
    working_capital: WorkingCapitalEstimate
    full_report_markdown: str
    per_buyer_emails: list[dict] = Field(default_factory=list)


# ─────────────────────────────────────────
# DB row mirrors (for insert helpers)
# ─────────────────────────────────────────

class ReportRow(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    manufacturer_id: Optional[uuid.UUID] = None
    hs_code: str
    origin_iso2: str
    target_iso2: str
    unit_cost_eur: Optional[float] = None
    tier: Literal["starter", "full"]
    status: Literal["queued", "running", "complete", "failed"] = "queued"
    is_test: bool = False
    paddle_transaction_id: Optional[str] = None
    pdf_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
