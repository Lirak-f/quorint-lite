"""LangGraph orchestrator — coordinates 5 workers, writes progress to Supabase."""

from __future__ import annotations

import os
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv

from models import ManufacturerInput, ReportSynthesis

load_dotenv()


def _supabase_client():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def _update_report_status(
    report_id: str,
    status: str,
    error_message: Optional[str] = None,
    worker_num: Optional[int] = None,
    extra: Optional[dict] = None,
) -> None:
    """Write report status + progress to Supabase. Fires Realtime event to frontend."""
    try:
        db = _supabase_client()
        update: dict[str, Any] = {"status": status}
        if error_message:
            update["error_message"] = error_message[:1000]
        if status == "complete":
            update["completed_at"] = datetime.now(timezone.utc).isoformat()
        if worker_num is not None:
            update["current_worker"] = worker_num
        if extra:
            update.update(extra)

        db.table("reports").update(update).eq("id", report_id).execute()

        if worker_num is not None:
            print(f"[Orchestrator] report {report_id}: worker {worker_num}/5 complete, status={status}")
    except Exception as e:
        print(f"[Orchestrator] Failed to update Supabase status for {report_id}: {e}")


def _save_worker_results(report_id: str, state: dict) -> None:
    """Persist worker outputs to Supabase after pipeline completion."""
    try:
        db = _supabase_client()

        demand = state.get("demand_output")
        if demand:
            row: dict[str, Any] = {
                "report_id": report_id,
                "import_value_usd": demand.import_value_usd,
                "cagr_5yr": float(demand.cagr_5yr) if demand.cagr_5yr is not None else None,
                "top_suppliers": [s.model_dump() for s in demand.top_suppliers] if demand.top_suppliers else None,
                "tariff_mfn": float(demand.tariff_mfn) if demand.tariff_mfn is not None else None,
                "tariff_preferential": float(demand.tariff_preferential) if demand.tariff_preferential is not None else None,
                "trade_agreement": demand.trade_agreement,
                "rca_score": float(demand.rca_score) if demand.rca_score is not None else None,
                "retail_p25_eur": demand.retail_p25_eur,
                "retail_median_eur": demand.retail_median_eur,
                "retail_p75_eur": demand.retail_p75_eur,
                "wholesale_low_eur": demand.wholesale_low_eur,
                "wholesale_high_eur": demand.wholesale_high_eur,
                "freight_low_eur": demand.freight_low_eur,
                "freight_high_eur": demand.freight_high_eur,
                "competitor_summary": demand.competitor_summary,
                "fx_volatility_90d": float(demand.fx_volatility_90d) if demand.fx_volatility_90d is not None else None,
            }
            lc = demand.landed_cost
            if lc:
                row["dap_per_unit_eur"] = lc.dap_per_unit_eur
                row["margin"] = float(lc.margin)
                row["margin_verdict"] = lc.margin_verdict
            db.table("report_demand").upsert(row).execute()

        compliance = state.get("compliance_output")
        if compliance:
            for item in compliance.items:
                db.table("report_compliance").insert({
                    "report_id": report_id,
                    "cert_id": item.cert_id,
                    "cert_name": item.cert_name,
                    "cert_type": item.cert_type,
                    "critical": item.critical,
                    "cost_low_eur": item.cost_low_eur,
                    "cost_high_eur": item.cost_high_eur,
                    "lead_time_min": item.lead_time_min,
                    "lead_time_max": item.lead_time_max,
                    "providers": item.providers,
                    "note": item.note,
                }).execute()

        buyer_list = state.get("buyer_list")
        if buyer_list:
            all_buyers = buyer_list.warm + buyer_list.cold
            for b in all_buyers:
                db.table("report_buyers").insert({
                    "report_id": report_id,
                    "company_name": b.company_name,
                    "company_domain": b.company_domain,
                    "city": b.city,
                    "country_iso2": b.country_iso2,
                    "buyer_type": b.buyer_type,
                    "contact_name": b.contact_name,
                    "contact_title": b.contact_title,
                    "contact_email": b.contact_email,
                    "linkedin_url": b.linkedin_url,
                    "enrichment_source": b.enrichment_source,
                    "receptiveness_score": b.receptiveness_score,
                    "receptiveness_signals": b.receptiveness_signals,
                    "tier": b.tier,
                }).execute()

        synthesis = state.get("synthesis_output")
        if synthesis:
            synthesis_update: dict[str, Any] = {
                "full_report_markdown": synthesis.full_report_markdown,
                "first_contact_email": synthesis.first_contact_email,
                "first_contact_subject_lines": synthesis.first_contact_subject_lines,
                "action_plan_markdown": synthesis.action_plan_markdown,
                "risk_flags_markdown": synthesis.risk_flags_markdown,
            }
            if synthesis.full_report_markdown:
                try:
                    from pdf.generator import generate_pdf
                    pdf_url = generate_pdf(synthesis.full_report_markdown, report_id)
                    synthesis_update["pdf_url"] = pdf_url
                    print(f"[Orchestrator] PDF generated for report {report_id}: {pdf_url}")
                except Exception as pdf_err:
                    print(f"[Orchestrator] PDF generation failed for {report_id}: {pdf_err}")
            db.table("reports").update(synthesis_update).eq("id", report_id).execute()

    except Exception as e:
        print(f"[Orchestrator] Failed to save worker results for {report_id}: {e}")


def run_pipeline(
    report_id: str,
    manufacturer: ManufacturerInput,
    tier: str = "full",
    is_test: bool = False,
    skip_supabase: bool = False,
) -> dict[str, Any]:
    """
    Run the full 5-worker pipeline synchronously.
    Writes progress to Supabase after each worker (unless skip_supabase=True).

    Returns the final pipeline state dict.
    On error: marks report as failed and returns state with error_message.
    """
    from pipeline.graph import _make_initial_state, build_pipeline_graph

    state = _make_initial_state(
        report_id=report_id,
        manufacturer=manufacturer,
        tier=tier,
        is_test=is_test,
    )

    if not skip_supabase:
        _update_report_status(report_id, "running")

    # Build the compiled LangGraph
    pipeline = build_pipeline_graph()

    # Node completion callbacks — write intermediate progress to Supabase
    worker_names = ["w1_market", "w2_compliance", "w3_buyers", "w4_deep_research", "w5_synthesis"]

    try:
        # Run the graph — LangGraph invokes nodes sequentially
        final_state = pipeline.invoke(state)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}"
        print(f"[Orchestrator] Pipeline failed for report {report_id}: {error_msg}")
        if not skip_supabase:
            _update_report_status(report_id, "failed", error_message=error_msg)
        return {**state, "status": "failed", "error_message": error_msg}

    # Save all worker results to Supabase
    if not skip_supabase:
        _save_worker_results(report_id, final_state)
        _update_report_status(report_id, "complete", worker_num=5)

    return final_state


def run_pipeline_with_progress(
    report_id: str,
    manufacturer: ManufacturerInput,
    tier: str = "full",
    is_test: bool = False,
) -> dict[str, Any]:
    """
    Run pipeline with per-worker Supabase progress updates.
    Uses a monkey-patched graph that calls _update_report_status after each node.
    """
    from pipeline.graph import _make_initial_state

    state = _make_initial_state(
        report_id=report_id,
        manufacturer=manufacturer,
        tier=tier,
        is_test=is_test,
    )
    _update_report_status(report_id, "running")

    workers = [
        ("w1_market", "demand_output", 1),
        ("w2_compliance", "compliance_output", 2),
        ("w3_buyers", "buyer_list", 3),
        ("w4_deep_research", "deep_research_output", 4),
        ("w5_synthesis", "synthesis_output", 5),
    ]

    from pipeline.graph import (
        node_w1_market, node_w2_compliance, node_w3_buyers,
        node_w4_deep_research, node_w5_synthesis,
    )
    node_fns = {
        "w1_market": node_w1_market,
        "w2_compliance": node_w2_compliance,
        "w3_buyers": node_w3_buyers,
        "w4_deep_research": node_w4_deep_research,
        "w5_synthesis": node_w5_synthesis,
    }

    for worker_key, output_key, worker_num in workers:
        try:
            state = node_fns[worker_key](state)
            _update_report_status(report_id, "running", worker_num=worker_num)
        except Exception as e:
            error_msg = f"Worker {worker_num} ({worker_key}) failed: {type(e).__name__}: {e}"
            print(f"[Orchestrator] {error_msg}\n{traceback.format_exc()[-600:]}")
            _update_report_status(report_id, "failed", error_message=error_msg)
            return {**state, "status": "failed", "error_message": error_msg}

    _save_worker_results(report_id, state)
    _update_report_status(report_id, "complete")
    return state
