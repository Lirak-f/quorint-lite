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
SUPPORTED_TARGET_COUNTRIES = {"AT", "DE", "IT", "FR", "NL", "CH"}


# ─────────────────────────────────────────
# Request / response models
# ─────────────────────────────────────────

class CreateReportRequest(BaseModel):
    hs_code: str = Field(..., description="4 or 6 numeric digits — entered by user")
    target_iso2: str = Field(..., min_length=2, max_length=2)
    unit_cost_eur: float = Field(..., gt=0)
    tier: str = Field("full", pattern="^(starter|full)$")
    certifications: list[str] = Field(default_factory=list)
    capacity_units: str = Field("<100/mo", pattern=r"^(<100/mo|100-500/mo|500\+/mo)$")
    company: Optional[str] = None


class CreateReportResponse(BaseModel):
    report_id: str
    checkout_url: str
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


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@router.post("/reports", response_model=CreateReportResponse, status_code=202)
async def create_report(
    body: CreateReportRequest,
    user: dict = Depends(require_auth),
) -> CreateReportResponse:
    """
    Create a new report job and return a Paddle checkout URL.

    Payment flow:
      1. Report row created with status='queued', no paddle_transaction_id yet.
      2. Paddle transaction created with report_id in custom_data.
      3. Frontend redirects customer to checkout_url (Paddle-hosted).
      4. Job is NOT enqueued until webhook confirms transaction.completed.
    """
    _validate_hs_code(body.hs_code)
    _validate_target(body.target_iso2)

    user_id: str = user["id"]
    origin_iso2 = user.get("user_metadata", {}).get("origin_iso2", "XK")

    db = _supabase()
    manufacturer_id = _get_or_create_manufacturer(db, user_id, origin_iso2, body.company)

    report_id = str(uuid.uuid4())
    db.table("reports").insert({
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
    }).execute()

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

    # Create Paddle transaction — job is held until webhook fires
    from paddle_client import paddle
    from paddle_billing.Resources.Transactions.Operations.CreateTransaction import CreateTransaction  # type: ignore[import-untyped]
    from paddle_billing.Entities.Shared import CollectionMode, CustomData

    price_id = _price_id_for_tier(body.tier)
    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")

    try:
        transaction = paddle.transactions.create(
            CreateTransaction(
                items=[{"price_id": price_id, "quantity": 1}],
                custom_data=CustomData({"report_id": report_id}),
                collection_mode=CollectionMode.Automatic,
                checkout={"url": f"{app_url}/reports/{report_id}"} if not app_url.startswith("http://localhost") else None,
            )
        )
    except Exception as e:
        # Roll back the report row so the user can retry
        db.table("reports").delete().eq("id", report_id).execute()
        raise HTTPException(status_code=502, detail=f"Could not create Paddle transaction: {e}")

    checkout_url = transaction.checkout.url
    if not checkout_url:
        db.table("reports").delete().eq("id", report_id).execute()
        raise HTTPException(status_code=502, detail="Paddle returned no checkout URL")

    if ph:
        ph.capture(
            distinct_id=user_id,
            event="checkout_initiated",
            properties={
                "report_id": report_id,
                "tier": body.tier,
                "target_iso2": body.target_iso2.upper(),
            },
        )

    return CreateReportResponse(
        report_id=report_id,
        checkout_url=checkout_url,
        status="queued",
    )


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
