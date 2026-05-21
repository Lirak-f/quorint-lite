"""Internal test report endpoint — gated by INTERNAL_TEST_TOKEN, bypasses Paddle."""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client
from typing import Annotated

load_dotenv()

from pipeline.orchestrator import run_pipeline  # noqa: E402

router = APIRouter()


class TestReportRequest(BaseModel):
    hs_code: str = Field(..., description="4 or 6 numeric digits")
    origin_iso2: str = Field("XK", min_length=2, max_length=2)
    target_iso2: str = Field(..., min_length=2, max_length=2)
    unit_cost_eur: float = Field(..., gt=0)
    tier: str = Field("full", pattern="^(starter|full)$")
    certifications: list[str] = Field(default_factory=list)
    capacity_units: str = Field("<100/mo")
    company: Optional[str] = None


@router.post("/reports/test")
async def create_test_report(
    body: TestReportRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """
    Run the full pipeline synchronously (no queue, no Paddle).
    Always generates tier='full', sets is_test=True.
    Gated by INTERNAL_TEST_TOKEN header.
    """
    token = os.getenv("INTERNAL_TEST_TOKEN")
    if not token or authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Invalid or missing INTERNAL_TEST_TOKEN")

    from models import ManufacturerInput

    manufacturer = ManufacturerInput(
        hs_code=body.hs_code,
        origin_iso2=body.origin_iso2,  # type: ignore[arg-type]
        target_iso2=body.target_iso2,
        unit_cost_eur=body.unit_cost_eur,
        tier="full",
        certifications=body.certifications,
        capacity_units=body.capacity_units,  # type: ignore[arg-type]
        company=body.company,
    )

    report_id = str(uuid.uuid4())

    # Create a report row in Supabase if available — non-fatal if DB not configured
    try:
        db = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
        db.table("reports").insert({
            "id": report_id,
            "hs_code": body.hs_code,
            "origin_iso2": body.origin_iso2,
            "target_iso2": body.target_iso2.upper(),
            "unit_cost_eur": body.unit_cost_eur,
            "tier": "full",
            "status": "queued",
            "is_test": True,
        }).execute()
    except Exception as e:
        print(f"[TestRoute] Supabase insert skipped (non-fatal): {e}")

    # Run pipeline synchronously — skip_supabase=False so results are persisted
    try:
        final_state = run_pipeline(
            report_id=report_id,
            manufacturer=manufacturer,
            tier="full",
            is_test=True,
            skip_supabase=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    if final_state.get("status") == "failed":
        raise HTTPException(status_code=500, detail=final_state.get("error_message", "Pipeline failed"))

    # Serialise final state for the response
    synthesis = final_state.get("synthesis_output")
    demand = final_state.get("demand_output")
    compliance = final_state.get("compliance_output")
    buyer_list = final_state.get("buyer_list")

    return {
        "report_id": report_id,
        "status": "complete",
        "is_test": True,
        "tier": "full",
        "demand": demand.model_dump() if demand else None,
        "compliance": compliance.model_dump() if compliance else None,
        "buyers": buyer_list.model_dump() if buyer_list else None,
        "synthesis": synthesis.model_dump() if synthesis else None,
    }
