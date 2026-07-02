"""Production report endpoints — Supabase JWT auth, Paddle-gated, BullMQ queue."""

from __future__ import annotations

import os
import re
import uuid
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from auth import require_auth
from posthog_client import get_posthog

router = APIRouter()

# Countries with freight benchmark coverage in the DB
SUPPORTED_TARGET_COUNTRIES = {"AT", "DE", "IT", "FR", "NL", "CH", "SE"}


# ─────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────

class CreateReportRequest(BaseModel):
    hs_code: str = Field(..., description="4 or 6 numeric digits — entered by user")
    origin_iso2: Optional[str] = Field(None, min_length=2, max_length=2)
    target_iso2: str = Field(..., min_length=2, max_length=2)
    unit_cost_eur: float = Field(..., gt=0)
    tier: str = Field("full", pattern="^(starter|full)$")
    certifications: list[str] = Field(default_factory=list)
    capacity_units: str = Field("<100/mo", pattern=r"^(<100/mo|100-500/mo|500\+/mo)$")
    company: Optional[str] = None
    product_name: Optional[str] = None
    product_desc: Optional[str] = None
    lead_count: Optional[int] = Field(None, ge=10, le=30)
    moq: Optional[int] = Field(None, gt=0)
    lead_time_days: Optional[int] = Field(None, gt=0)
    # Product profile (Step 1b)
    product_phrase: Optional[str] = None
    end_buyer_type: Optional[str] = None
    price_tier: Optional[str] = None
    packaging_format: Optional[list[str]] = None
    material_subtype: Optional[str] = None
    processing_level: Optional[str] = None


class CreateReportResponse(BaseModel):
    report_id: str
    price_id: str
    status: str = "queued"


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _validate_hs_code(hs_code: str) -> None:
    if not re.fullmatch(r"\d{4}|\d{6}", hs_code):
        raise HTTPException(status_code=422, detail="hs_code must be exactly 4 or 6 numeric digits")


def _validate_target(target_iso2: str) -> None:
    if target_iso2.upper() not in SUPPORTED_TARGET_COUNTRIES:
        raise HTTPException(
            status_code=422,
            detail=f"target_iso2 '{target_iso2}' not supported. Supported: {sorted(SUPPORTED_TARGET_COUNTRIES)}",
        )


def _supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return create_client(url, key)


def _get_or_create_manufacturer(db, user_id: str, origin_iso2: str, company: Optional[str]) -> str:
    """Return manufacturer.id for this user, creating the row if it doesn't exist."""
    result = db.table("manufacturers").select("id").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]["id"]

    new_id = str(uuid.uuid4())
    db.table("manufacturers").insert({
        "id": new_id,
        "user_id": user_id,
        "origin_iso2": origin_iso2,
        "company": company,
    }).execute()
    return new_id


def _price_id_for_tier(tier: str) -> str:
    key = "PADDLE_PRICE_ID_FULL" if tier == "full" else "PADDLE_PRICE_ID_STARTER"
    price_id = os.getenv(key)
    if not price_id:
        raise HTTPException(status_code=500, detail=f"{key} not configured")
    return price_id


_WB6_ORIGINS = {"XK", "AL", "RS", "BA", "MK", "ME"}


def _resolve_origin_iso2(body: CreateReportRequest, user: dict) -> str:
    if body.origin_iso2:
        origin = body.origin_iso2.upper()
        if origin not in _WB6_ORIGINS:
            raise HTTPException(
                status_code=422,
                detail=f"origin_iso2 '{origin}' not supported. Supported: {sorted(_WB6_ORIGINS)}",
            )
        return origin
    return user.get("user_metadata", {}).get("origin_iso2", "XK").upper()


def _is_unknown_column_error(exc: Exception) -> bool:
    err = getattr(exc, "message", None) or str(exc)
    if isinstance(err, dict):
        err = err.get("message", str(err))
    return "Could not find the" in str(err) and "column" in str(err)


def _insert_report_row(db, report_row: dict[str, Any]) -> None:
    """Insert report row; fall back to core columns if optional fields are not migrated yet."""
    core_keys = {
        "id", "manufacturer_id", "hs_code", "origin_iso2", "target_iso2",
        "unit_cost_eur", "tier", "status", "is_test", "certifications", "capacity_units",
    }
    try:
        db.table("reports").insert(report_row).execute()
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise HTTPException(status_code=502, detail=f"Could not save report: {exc}") from exc
        core_row = {k: v for k, v in report_row.items() if k in core_keys}
        try:
            db.table("reports").insert(core_row).execute()
        except Exception as retry_exc:
            raise HTTPException(status_code=502, detail=f"Could not save report: {retry_exc}") from retry_exc
        print(
            "[reports] Optional report columns missing — run supabase db push. "
            f"Dropped keys: {sorted(set(report_row) - core_keys)}"
        )


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@router.post("/reports", response_model=CreateReportResponse, status_code=202)
async def create_report(
    body: CreateReportRequest,
    user: dict = Depends(require_auth),
) -> CreateReportResponse:
    """
    Create a new report job and return the price_id for Paddle overlay checkout.

    Payment flow:
      1. Report row created with status='queued'.
      2. Frontend opens Paddle overlay with price_id and report_id in customData.
      3. Job is NOT enqueued until webhook confirms transaction.completed.
    """
    _validate_hs_code(body.hs_code)
    _validate_target(body.target_iso2)

    user_id: str = user["id"]
    origin_iso2 = _resolve_origin_iso2(body, user)

    db = _supabase()
    company = body.company or body.product_name
    manufacturer_id = _get_or_create_manufacturer(db, user_id, origin_iso2, company)

    report_id = str(uuid.uuid4())
    report_row: dict[str, Any] = {
        "id": report_id,
        "manufacturer_id": manufacturer_id,
        "hs_code": body.hs_code,
        "origin_iso2": origin_iso2,
        "target_iso2": body.target_iso2.upper(),
        "unit_cost_eur": body.unit_cost_eur,
        "tier": body.tier,
        "status": "queued",
        "is_test": False,
        "certifications": body.certifications,
        "capacity_units": body.capacity_units,
    }
    if body.product_name:
        report_row["product_name"] = body.product_name
    if body.product_desc:
        report_row["product_desc"] = body.product_desc
    if body.lead_count is not None:
        report_row["lead_count"] = body.lead_count
    if body.moq is not None:
        report_row["moq"] = body.moq
    if body.lead_time_days is not None:
        report_row["lead_time_days"] = body.lead_time_days
    if body.product_phrase:
        report_row["product_phrase"] = body.product_phrase
    if body.end_buyer_type:
        report_row["end_buyer_type"] = body.end_buyer_type
    if body.price_tier:
        report_row["price_tier"] = body.price_tier
    if body.packaging_format:
        report_row["packaging_format"] = body.packaging_format
    if body.material_subtype:
        report_row["material_subtype"] = body.material_subtype
    if body.processing_level:
        report_row["processing_level"] = body.processing_level

    _insert_report_row(db, report_row)

    ph = get_posthog()
    if ph:
        ph.capture(
            distinct_id=user_id,
            event="report_created",
            properties={
                "report_id": report_id,
                "hs_code": body.hs_code,
                "origin_iso2": origin_iso2,
                "target_iso2": body.target_iso2.upper(),
                "tier": body.tier,
                "capacity_units": body.capacity_units,
                "certifications_count": len(body.certifications),
            },
        )

    price_id = _price_id_for_tier(body.tier)
    return CreateReportResponse(report_id=report_id, price_id=price_id, status="queued")


@router.post("/reports/{report_id}/run", status_code=202)
async def run_report(
    report_id: str,
    user: dict = Depends(require_auth),
) -> dict[str, str]:
    """
    Trigger pipeline execution for a queued report.
    Idempotent: no-ops if report is already running or complete.
    Caller must own the report.
    """
    user_id: str = user["id"]
    db = _supabase()

    result = db.table("reports").select(
        "*, manufacturers!inner(user_id)"
    ).eq("id", report_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    row = result.data[0]
    mfr = row.get("manufacturers") or {}
    if mfr.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your report")

    status = row.get("status", "queued")
    if status in ("running", "complete"):
        return {"status": status}

    # Start pipeline in background thread — same fallback path as webhook
    import threading
    from models import ManufacturerInput
    from pipeline.orchestrator import run_pipeline

    raw_cost = row.get("unit_cost_eur")
    if raw_cost is None:
        raise HTTPException(status_code=400, detail="unit_cost_eur is missing from the report")
    unit_cost = float(raw_cost)
    if unit_cost <= 0:
        raise HTTPException(status_code=400, detail="unit_cost_eur must be greater than 0")

    manufacturer = ManufacturerInput(
        hs_code=row["hs_code"],
        origin_iso2=row["origin_iso2"],
        target_iso2=row["target_iso2"],
        unit_cost_eur=unit_cost,
        tier=row.get("tier", "full"),
        certifications=row.get("certifications") or [],
        capacity_units=row.get("capacity_units") or "<100/mo",
        company=None,
        product_name=row.get("product_name"),
        product_desc=row.get("product_desc"),
        product_phrase=row.get("product_phrase"),
        end_buyer_type=row.get("end_buyer_type"),
        price_tier=row.get("price_tier"),
        packaging_format=row.get("packaging_format"),
        material_subtype=row.get("material_subtype"),
        processing_level=row.get("processing_level"),
    )

    def _run():
        run_pipeline(
            report_id=report_id,
            manufacturer=manufacturer,
            tier=row.get("tier", "full"),
            is_test=row.get("is_test", False),
        )

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "running"}


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Return report status and data. Caller must own the report."""
    user_id: str = user["id"]
    db = _supabase()

    result = db.table("reports").select(
        "*, manufacturers!inner(user_id)"
    ).eq("id", report_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    row = result.data[0]
    mfr = row.get("manufacturers") or {}
    if mfr.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not your report")

    report: dict[str, Any] = {
        "report_id": row["id"],
        "status": row["status"],
        "tier": row["tier"],
        "hs_code": row["hs_code"],
        "origin_iso2": row["origin_iso2"],
        "target_iso2": row["target_iso2"],
        "created_at": row.get("created_at"),
        "completed_at": row.get("completed_at"),
        "pdf_url": row.get("pdf_url"),
        "error_message": row.get("error_message"),
    }

    if row["status"] == "complete":
        demand = db.table("report_demand").select("*").eq("report_id", report_id).execute()
        compliance = db.table("report_compliance").select("*").eq("report_id", report_id).execute()
        buyers = db.table("report_buyers").select("*").eq("report_id", report_id).execute()

        report["sections"] = {
            "demand": demand.data[0] if demand.data else None,
            "compliance": compliance.data,
            "buyers": buyers.data,
        }

        ph = get_posthog()
        if ph:
            ph.capture(
                distinct_id=user_id,
                event="report_viewed",
                properties={
                    "report_id": report_id,
                    "hs_code": row["hs_code"],
                    "origin_iso2": row["origin_iso2"],
                    "target_iso2": row["target_iso2"],
                    "tier": row["tier"],
                },
            )

    return report
