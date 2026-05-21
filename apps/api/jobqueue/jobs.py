"""Report generation job schema and enqueue helper for BullMQ + Redis."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

QUEUE_NAME = "report-generation"


class ReportJob:
    """Typed wrapper for a report generation job payload."""

    def __init__(
        self,
        report_id: str,
        hs_code: str,
        origin_iso2: str,
        target_iso2: str,
        unit_cost_eur: float,
        tier: str = "full",
        is_test: bool = False,
        certifications: Optional[list[str]] = None,
        capacity_units: str = "<100/mo",
        company: Optional[str] = None,
    ):
        self.report_id = report_id
        self.hs_code = hs_code
        self.origin_iso2 = origin_iso2
        self.target_iso2 = target_iso2
        self.unit_cost_eur = unit_cost_eur
        self.tier = tier
        self.is_test = is_test
        self.certifications = certifications or []
        self.capacity_units = capacity_units
        self.company = company

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "hs_code": self.hs_code,
            "origin_iso2": self.origin_iso2,
            "target_iso2": self.target_iso2,
            "unit_cost_eur": self.unit_cost_eur,
            "tier": self.tier,
            "is_test": self.is_test,
            "certifications": self.certifications,
            "capacity_units": self.capacity_units,
            "company": self.company,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportJob":
        return cls(
            report_id=data["report_id"],
            hs_code=data["hs_code"],
            origin_iso2=data["origin_iso2"],
            target_iso2=data["target_iso2"],
            unit_cost_eur=float(data["unit_cost_eur"]),
            tier=data.get("tier", "full"),
            is_test=data.get("is_test", False),
            certifications=data.get("certifications", []),
            capacity_units=data.get("capacity_units", "<100/mo"),
            company=data.get("company"),
        )


def enqueue_report(job_data: dict[str, Any]) -> str:
    """
    Push a report job onto the BullMQ Redis queue.
    Returns the job_id (same as report_id for traceability).

    Uses Redis LPUSH into a BullMQ-compatible key format.
    BullMQ JS worker on the frontend consumes from the same queue.
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise EnvironmentError("REDIS_URL not set")

    try:
        import redis as redis_lib
    except ImportError:
        raise RuntimeError("redis-py not installed. Run: pip install redis")

    r = redis_lib.from_url(redis_url, decode_responses=True)

    job_id = job_data.get("report_id", str(uuid.uuid4()))
    job_payload = json.dumps({
        "id": job_id,
        "data": job_data,
        "opts": {
            "attempts": 3,
            "backoff": {"type": "exponential", "delay": 5000},
        },
        "timestamp": int(__import__("time").time() * 1000),
    })

    # BullMQ queue key format: bull:{queue_name}:waiting
    queue_key = f"bull:{QUEUE_NAME}:waiting"
    r.rpush(queue_key, job_payload)

    print(f"[Queue] Enqueued report job {job_id} to {queue_key}")
    return job_id
