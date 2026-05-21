"""Paddle webhook handler — verifies signature, enqueues report job on payment."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

load_dotenv()

router = APIRouter()


def _supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase env vars not set")
    return create_client(url, key)


def _enqueue_report_job(report_id: str) -> None:
    """Push report job onto BullMQ Redis queue."""
    db = _supabase()

    result = db.table("reports").select("*").eq("id", report_id).execute()
    if not result.data:
        print(f"[Webhook] Report {report_id} not found in DB — cannot enqueue")
        return

    row = result.data[0]

    from jobqueue.jobs import enqueue_report
    enqueue_report({
        "report_id": report_id,
        "hs_code": row["hs_code"],
        "origin_iso2": row["origin_iso2"],
        "target_iso2": row["target_iso2"],
        "unit_cost_eur": float(row.get("unit_cost_eur") or 0),
        "tier": row.get("tier", "full"),
        "is_test": False,
        "certifications": row.get("certifications") or [],
        "capacity_units": row.get("capacity_units") or "<100/mo",
    })


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

    try:
        _enqueue_report_job(report_id)
    except Exception as e:
        print(f"[Webhook] Failed to enqueue report {report_id}: {e}")
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
