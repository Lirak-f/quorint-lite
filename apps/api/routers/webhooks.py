"""Paddle webhook handler — verifies signature, enqueues report job on payment."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

load_dotenv()

from posthog_client import get_posthog

router = APIRouter()


def _supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase env vars not set")
    return create_client(url, key)


def _enqueue_report_job(report_id: str) -> None:
    """Push report job onto BullMQ Redis queue, falling back to an inline background thread if Redis is unreachable."""
    db = _supabase()

    result = db.table("reports").select("*").eq("id", report_id).execute()
    if not result.data:
        print(f"[Webhook] Report {report_id} not found in DB — cannot enqueue")
        return

    row = result.data[0]
    job_data = {
        "report_id": report_id,
        "hs_code": row["hs_code"],
        "origin_iso2": row["origin_iso2"],
        "target_iso2": row["target_iso2"],
        "unit_cost_eur": float(row.get("unit_cost_eur") or 0),
        "tier": row.get("tier", "full"),
        "is_test": False,
        "certifications": row.get("certifications") or [],
        "capacity_units": row.get("capacity_units") or "<100/mo",
        "product_name": row.get("product_name"),
        "product_desc": row.get("product_desc"),
        "product_phrase": row.get("product_phrase"),
        "end_buyer_type": row.get("end_buyer_type"),
        "price_tier": row.get("price_tier"),
        "packaging_format": row.get("packaging_format"),
        "material_subtype": row.get("material_subtype"),
        "processing_level": row.get("processing_level"),
    }

    try:
        from jobqueue.jobs import enqueue_report
        enqueue_report(job_data)
        print(f"[Webhook] Enqueued report {report_id} to Redis queue")
    except Exception as redis_err:
        print(f"[Webhook] Redis unavailable ({redis_err}) — running pipeline inline in background thread")
        import threading
        from models import ManufacturerInput
        from pipeline.orchestrator import run_pipeline

        def _run():
            manufacturer = ManufacturerInput(
                hs_code=job_data["hs_code"],
                origin_iso2=job_data["origin_iso2"],
                target_iso2=job_data["target_iso2"],
                unit_cost_eur=job_data["unit_cost_eur"],
                tier=job_data["tier"],
                certifications=job_data["certifications"],
                capacity_units=job_data["capacity_units"],
                product_name=job_data.get("product_name"),
                product_desc=job_data.get("product_desc"),
                product_phrase=job_data.get("product_phrase"),
                end_buyer_type=job_data.get("end_buyer_type"),
                price_tier=job_data.get("price_tier"),
                packaging_format=job_data.get("packaging_format"),
                material_subtype=job_data.get("material_subtype"),
                processing_level=job_data.get("processing_level"),
            )
            run_pipeline(report_id=report_id, manufacturer=manufacturer, tier=job_data["tier"], is_test=False)

        threading.Thread(target=_run, daemon=True).start()


@router.post("/webhooks/paddle")
async def paddle_webhook(request: Request) -> dict[str, str]:
    """
    Receive Paddle webhook notifications.

    Events handled:
      transaction.completed  — record paddle_transaction_id, enqueue pipeline job
      subscription.activated — mark manufacturer copilot subscription active
      subscription.canceled  — mark manufacturer copilot subscription canceled
    """
    webhook_secret = os.getenv("PADDLE_NOTIFICATION_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="PADDLE_NOTIFICATION_WEBHOOK_SECRET not configured")

    payload = await request.body()

    # Verify Paddle signature
    try:
        from paddle_billing.Notifications import Secret, Verifier
        integrity_check = Verifier().verify(request, Secret(webhook_secret))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature verification error: {e}")

    if not integrity_check:
        raise HTTPException(status_code=400, detail="Invalid Paddle webhook signature")

    # Parse the notification
    try:
        import json
        body = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type: str = body.get("event_type", "")
    data: dict[str, Any] = body.get("data", {})

    if event_type == "transaction.completed":
        _handle_transaction_completed(data)

    elif event_type == "subscription.activated":
        _handle_subscription_event("activated", data)

    elif event_type == "subscription.canceled":
        _handle_subscription_event("canceled", data)

    return {"status": "ok"}


def _handle_transaction_completed(data: dict[str, Any]) -> None:
    """Record paddle_transaction_id on report and enqueue the pipeline job."""
    custom_data: dict[str, Any] = data.get("custom_data") or {}
    report_id = custom_data.get("report_id")

    if not report_id:
        print("[Webhook] transaction.completed — no report_id in custom_data, skipping")
        return

    paddle_transaction_id: str = data.get("id", "")

    db = _supabase()
    db.table("reports").update({
        "paddle_transaction_id": paddle_transaction_id,
    }).eq("id", report_id).execute()

    print(f"[Webhook] Payment confirmed for report {report_id} — enqueuing job")

    ph = get_posthog()
    if ph:
        ph.capture(
            distinct_id=report_id,
            event="payment_completed",
            properties={
                "report_id": report_id,
                "paddle_transaction_id": paddle_transaction_id,
            },
        )

    try:
        _enqueue_report_job(report_id)
        if ph:
            ph.capture(
                distinct_id=report_id,
                event="report_pipeline_started",
                properties={"report_id": report_id},
            )
    except Exception as e:
        print(f"[Webhook] Failed to enqueue report {report_id}: {e}")
        if ph:
            ph.capture(
                distinct_id=report_id,
                event="report_pipeline_failed",
                properties={"report_id": report_id, "error": str(e)},
            )
        db.table("reports").update({
            "status": "failed",
            "error_message": f"Failed to start report after payment: {e}",
        }).eq("id", report_id).execute()


def _handle_subscription_event(event: str, data: dict[str, Any]) -> None:
    """Update manufacturer subscription status for Copilot tier."""
    paddle_subscription_id: str = data.get("id", "")
    customer_id: str = data.get("customer_id", "")
    is_active = event == "activated"

    print(f"[Webhook] subscription.{event} — subscription {paddle_subscription_id}, customer {customer_id}")

    if not paddle_subscription_id:
        return

    db = _supabase()

    try:
        if is_active:
            db.table("manufacturers").update({
                "subscription_status": "active",
                "paddle_subscription_id": paddle_subscription_id,
            }).eq("paddle_subscription_id", paddle_subscription_id).execute()
        else:
            db.table("manufacturers").update({
                "subscription_status": "canceled",
            }).eq("paddle_subscription_id", paddle_subscription_id).execute()
    except Exception as e:
        print(f"[Webhook] Could not update manufacturer subscription status: {e}")

    ph = get_posthog()
    if ph:
        ph.capture(
            distinct_id=paddle_subscription_id,
            event="subscription_activated" if is_active else "subscription_canceled",
            properties={"paddle_subscription_id": paddle_subscription_id},
        )
