"""
Route-level API tests using FastAPI TestClient.

These tests exercise HTTP behaviour (auth, validation, routing) without
running the real pipeline. Supabase and Redis calls are patched so the
suite runs without external services.

Run: cd apps/api && python -m pytest tests/test_api.py -v
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Allow imports from apps/api/
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set minimal env vars before importing the app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("INTERNAL_TEST_TOKEN", "test-secret-token")
os.environ.setdefault("PADDLE_NOTIFICATION_WEBHOOK_SECRET", "pdl_ntfset_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

VALID_REPORT_BODY = {
    "hs_code": "940360",
    "target_iso2": "AT",
    "unit_cost_eur": 200.0,
    "tier": "full",
    "certifications": [],
    "capacity_units": "<100/mo",
}

INTERNAL_TOKEN_HEADER = {"Authorization": "Bearer test-secret-token"}

VALID_TEST_BODY = {
    "hs_code": "940360",
    "origin_iso2": "XK",
    "target_iso2": "AT",
    "unit_cost_eur": 200.0,
}


def _mock_supabase_client(insert_ok: bool = True) -> MagicMock:
    """Return a mock Supabase client whose chained calls succeed."""
    db = MagicMock()
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=[])
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "mock-mfr"}])
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(data=[])
    return db


# ─────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────

def test_health_returns_200():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


# ─────────────────────────────────────────
# POST /api/reports — auth required
# ─────────────────────────────────────────

def test_create_report_no_auth_returns_401():
    resp = client.post("/api/reports", json=VALID_REPORT_BODY)
    assert resp.status_code == 401


def test_create_report_invalid_token_returns_401():
    with patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify:
        from fastapi import HTTPException
        mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid or expired token")
        resp = client.post(
            "/api/reports",
            json=VALID_REPORT_BODY,
            headers={"Authorization": "Bearer bad-token"},
        )
    assert resp.status_code == 401


def test_create_report_bad_hs_code_returns_422():
    with patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"id": "user-123", "user_metadata": {}}
        resp = client.post(
            "/api/reports",
            json={**VALID_REPORT_BODY, "hs_code": "123"},  # 3 digits — invalid
            headers={"Authorization": "Bearer valid-token"},
        )
    assert resp.status_code == 422


def test_create_report_unsupported_country_returns_422():
    with patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"id": "user-123", "user_metadata": {}}
        resp = client.post(
            "/api/reports",
            json={**VALID_REPORT_BODY, "target_iso2": "JP"},  # not in supported list
            headers={"Authorization": "Bearer valid-token"},
        )
    assert resp.status_code == 422


def test_create_report_zero_cost_returns_422():
    with patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"id": "user-123", "user_metadata": {}}
        resp = client.post(
            "/api/reports",
            json={**VALID_REPORT_BODY, "unit_cost_eur": 0},
            headers={"Authorization": "Bearer valid-token"},
        )
    assert resp.status_code == 422


def test_create_report_valid_enqueues_and_returns_report_id():
    mock_db = _mock_supabase_client()
    # Simulate no existing manufacturer → insert returns new id
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "mfr-123"}])

    with (
        patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify,
        patch("routers.reports._supabase", return_value=mock_db),
    ):
        mock_verify.return_value = {"id": "user-123", "user_metadata": {}}
        resp = client.post(
            "/api/reports",
            json=VALID_REPORT_BODY,
            headers={"Authorization": "Bearer valid-token"},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert "report_id" in body
    assert body["status"] == "queued"


# ─────────────────────────────────────────
# GET /api/reports/{report_id} — auth required
# ─────────────────────────────────────────

def test_get_report_no_auth_returns_401():
    resp = client.get(f"/api/reports/{uuid.uuid4()}")
    assert resp.status_code == 401


def test_get_report_wrong_user_returns_403():
    report_id = str(uuid.uuid4())
    mock_db = _mock_supabase_client()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{
            "id": report_id,
            "status": "queued",
            "tier": "full",
            "hs_code": "940360",
            "origin_iso2": "XK",
            "target_iso2": "AT",
            "created_at": "2026-05-01T00:00:00Z",
            "completed_at": None,
            "pdf_url": None,
            "error_message": None,
            "manufacturers": {"user_id": "other-user"},
        }]
    )

    with (
        patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify,
        patch("routers.reports._supabase", return_value=mock_db),
    ):
        mock_verify.return_value = {"id": "user-123"}
        resp = client.get(
            f"/api/reports/{report_id}",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert resp.status_code == 403


def test_get_report_not_found_returns_404():
    report_id = str(uuid.uuid4())
    mock_db = _mock_supabase_client()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    with (
        patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify,
        patch("routers.reports._supabase", return_value=mock_db),
    ):
        mock_verify.return_value = {"id": "user-123"}
        resp = client.get(
            f"/api/reports/{report_id}",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert resp.status_code == 404


def test_get_report_owner_gets_status():
    report_id = str(uuid.uuid4())
    mock_db = _mock_supabase_client()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{
            "id": report_id,
            "status": "queued",
            "tier": "full",
            "hs_code": "940360",
            "origin_iso2": "XK",
            "target_iso2": "AT",
            "created_at": "2026-05-01T00:00:00Z",
            "completed_at": None,
            "pdf_url": None,
            "error_message": None,
            "manufacturers": {"user_id": "user-123"},
        }]
    )

    with (
        patch("auth._verify_jwt_with_supabase", new_callable=AsyncMock) as mock_verify,
        patch("routers.reports._supabase", return_value=mock_db),
    ):
        mock_verify.return_value = {"id": "user-123"}
        resp = client.get(
            f"/api/reports/{report_id}",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_id"] == report_id
    assert body["status"] == "queued"


# ─────────────────────────────────────────
# POST /api/reports/test — INTERNAL_TEST_TOKEN
# ─────────────────────────────────────────

def test_test_route_no_token_returns_401():
    resp = client.post("/api/reports/test", json=VALID_TEST_BODY)
    assert resp.status_code == 401


def test_test_route_wrong_token_returns_401():
    resp = client.post(
        "/api/reports/test",
        json=VALID_TEST_BODY,
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_test_route_valid_token_runs_pipeline():
    """Pipeline is mocked — verifies the route calls run_pipeline and returns complete."""
    from models import ManufacturerInput, ReportSynthesis, WorkingCapitalEstimate

    mock_synthesis = MagicMock(spec=ReportSynthesis)
    mock_synthesis.model_dump.return_value = {"full_report_markdown": "# Report"}

    mock_final_state: dict[str, Any] = {
        "status": "complete",
        "demand_output": None,
        "compliance_output": None,
        "buyer_list": None,
        "synthesis_output": mock_synthesis,
    }

    with (
        patch("routers.test_reports.run_pipeline", return_value=mock_final_state) as mock_pipeline,
        patch("routers.test_reports.create_client") as mock_supabase,
    ):
        mock_supabase.return_value = _mock_supabase_client()
        resp = client.post(
            "/api/reports/test",
            json=VALID_TEST_BODY,
            headers=INTERNAL_TOKEN_HEADER,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["is_test"] is True
    assert body["tier"] == "full"
    assert "report_id" in body
    mock_pipeline.assert_called_once()

    call_kwargs = mock_pipeline.call_args
    assert call_kwargs.kwargs.get("is_test") is True
    assert call_kwargs.kwargs.get("tier") == "full"


def test_test_route_pipeline_failure_returns_500():
    mock_final_state: dict[str, Any] = {
        "status": "failed",
        "error_message": "Worker 1 crashed",
    }

    with (
        patch("routers.test_reports.run_pipeline", return_value=mock_final_state),
        patch("routers.test_reports.create_client") as mock_supabase,
    ):
        mock_supabase.return_value = _mock_supabase_client()
        resp = client.post(
            "/api/reports/test",
            json=VALID_TEST_BODY,
            headers=INTERNAL_TOKEN_HEADER,
        )

    assert resp.status_code == 500


# ─────────────────────────────────────────
# POST /api/webhooks/paddle
# ─────────────────────────────────────────

def test_paddle_webhook_invalid_signature_returns_400():
    """Verifier returning False → 400."""
    with patch("routers.webhooks.Verifier") as mock_verifier_cls:
        mock_verifier_cls.return_value.verify.return_value = False
        resp = client.post(
            "/api/webhooks/paddle",
            content=b'{"event_type":"transaction.completed","data":{}}',
        )
    assert resp.status_code == 400


def test_paddle_webhook_transaction_completed_enqueues_job():
    report_id = str(uuid.uuid4())
    payload = {
        "event_type": "transaction.completed",
        "data": {
            "id": "txn_test_123",
            "custom_data": {"report_id": report_id},
        },
    }
    import json

    mock_db = _mock_supabase_client()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{
            "id": report_id,
            "hs_code": "940360",
            "origin_iso2": "XK",
            "target_iso2": "AT",
            "unit_cost_eur": 200.0,
            "tier": "full",
            "certifications": [],
            "capacity_units": "<100/mo",
        }]
    )

    with (
        patch("paddle_billing.Notifications.Verifier") as mock_verifier_cls,
        patch("routers.webhooks._supabase", return_value=mock_db),
        patch("routers.webhooks._enqueue_report_job") as mock_enqueue,
    ):
        mock_verifier_cls.return_value.verify.return_value = True
        resp = client.post(
            "/api/webhooks/paddle",
            content=json.dumps(payload).encode(),
        )

    assert resp.status_code == 200
    mock_enqueue.assert_called_once_with(report_id)


def test_paddle_webhook_subscription_activated_updates_manufacturer():
    paddle_sub_id = "sub_test_456"
    payload = {
        "event_type": "subscription.activated",
        "data": {
            "id": paddle_sub_id,
            "customer_id": "ctm_test_789",
        },
    }
    import json

    mock_db = _mock_supabase_client()

    with (
        patch("paddle_billing.Notifications.Verifier") as mock_verifier_cls,
        patch("routers.webhooks._supabase", return_value=mock_db),
    ):
        mock_verifier_cls.return_value.verify.return_value = True
        resp = client.post(
            "/api/webhooks/paddle",
            content=json.dumps(payload).encode(),
        )

    assert resp.status_code == 200
    # Verify the update was attempted on manufacturers table
    mock_db.table.assert_any_call("manufacturers")
