"""BullMQ-compatible Python worker — picks up report jobs from Redis and runs the pipeline."""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Optional

# Allow running from apps/api/
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


QUEUE_NAME = "report-generation"
POLL_INTERVAL_SECONDS = 2
MAX_RETRIES = 3


def _get_redis():
    try:
        import redis as redis_lib
    except ImportError:
        raise RuntimeError("redis-py not installed. Run: pip install redis")

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise EnvironmentError("REDIS_URL not set")
    return redis_lib.from_url(redis_url, decode_responses=True)


def _process_job(job_data: dict[str, Any]) -> None:
    """Run the pipeline for one job, update Supabase, generate PDF."""
    from models import ManufacturerInput
    from pipeline.orchestrator import run_pipeline_with_progress
    from pdf.generator import generate_pdf

    report_id = job_data.get("report_id")
    if not report_id:
        print(f"[Worker] Job missing report_id — skipping")
        return

    print(f"[Worker] Processing report {report_id}")

    try:
        manufacturer = ManufacturerInput(
            hs_code=job_data["hs_code"],
            origin_iso2=job_data["origin_iso2"],
            target_iso2=job_data["target_iso2"],
            unit_cost_eur=float(job_data["unit_cost_eur"]),
            tier=job_data.get("tier", "full"),
            certifications=job_data.get("certifications", []),
            capacity_units=job_data.get("capacity_units", "<100/mo"),
            company=job_data.get("company"),
        )
        tier = job_data.get("tier", "full")
        is_test = job_data.get("is_test", False)

        # Run the full pipeline with per-worker Supabase progress updates
        final_state = run_pipeline_with_progress(
            report_id=report_id,
            manufacturer=manufacturer,
            tier=tier,
            is_test=is_test,
        )

        if final_state.get("status") == "failed":
            print(f"[Worker] Pipeline failed for report {report_id}: {final_state.get('error_message')}")
            return

        # Generate PDF from synthesised report markdown
        synthesis = final_state.get("synthesis_output")
        if synthesis and synthesis.full_report_markdown:
            try:
                pdf_url = generate_pdf(synthesis.full_report_markdown, report_id)

                # Save pdf_url to Supabase
                from supabase import create_client
                db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
                db.table("reports").update({"pdf_url": pdf_url}).eq("id", report_id).execute()
                print(f"[Worker] PDF URL saved for report {report_id}: {pdf_url[:60]}...")
            except Exception as pdf_err:
                print(f"[Worker] PDF generation failed for {report_id}: {pdf_err}")
                # Non-fatal: report is still complete even without PDF

        print(f"[Worker] Completed report {report_id}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()[-600:]}"
        print(f"[Worker] Fatal error for report {report_id}: {error_msg}")

        # Mark report as failed in Supabase
        try:
            from supabase import create_client
            db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
            db.table("reports").update({
                "status": "failed",
                "error_message": error_msg[:1000],
            }).eq("id", report_id).execute()
        except Exception as db_err:
            print(f"[Worker] Failed to update Supabase error status: {db_err}")


def _poll_once(r) -> bool:
    """
    Pop one job from the Redis queue and process it.
    Returns True if a job was processed, False if queue was empty.
    """
    waiting_key = f"bull:{QUEUE_NAME}:waiting"
    active_key = f"bull:{QUEUE_NAME}:active"

    # Atomic move from waiting → active (BullMQ pattern)
    raw = r.lmove(waiting_key, active_key, "LEFT", "RIGHT")
    if not raw:
        return False

    try:
        envelope = json.loads(raw)
        job_data = envelope.get("data", envelope)
        _process_job(job_data)
    except json.JSONDecodeError as e:
        print(f"[Worker] Failed to parse job payload: {e} — raw: {raw[:200]}")
    except Exception as e:
        print(f"[Worker] Unhandled error processing job: {e}\n{traceback.format_exc()}")
    finally:
        # Remove from active queue regardless of outcome
        try:
            r.lrem(active_key, 1, raw)
        except Exception:
            pass

    return True


def run_worker_loop() -> None:
    """Main loop: continuously poll Redis for jobs and process them."""
    print(f"[Worker] Starting Quorint pipeline worker — queue: {QUEUE_NAME}")
    print(f"[Worker] Poll interval: {POLL_INTERVAL_SECONDS}s")

    r = _get_redis()
    print(f"[Worker] Connected to Redis")

    idle_count = 0
    while True:
        try:
            processed = _poll_once(r)
            if processed:
                idle_count = 0
            else:
                idle_count += 1
                if idle_count % 30 == 0:
                    print(f"[Worker] Idle — waiting for jobs ({idle_count * POLL_INTERVAL_SECONDS}s)")
                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[Worker] Shutting down")
            break
        except Exception as e:
            print(f"[Worker] Loop error: {e} — retrying in 5s")
            time.sleep(5)


if __name__ == "__main__":
    run_worker_loop()
