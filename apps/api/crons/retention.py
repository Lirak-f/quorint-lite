"""
Retention trigger cron jobs — three APScheduler tasks that re-engage manufacturers.

Scheduled from main.py lifespan on app startup.

  check_tariff_changes()  — weekly    — email if tariff changed on HS × target
  check_new_buyers()      — monthly   — email if new buyers found in Apollo
  day30_reengagement()    — daily     — email if report is 30+ days old, no prior trigger
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────
# DB + email helpers
# ─────────────────────────────────────────

def _supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise EnvironmentError("Supabase env vars not set")
    return create_client(url, key)


def _send_email(to: str, subject: str, html: str) -> None:
    """Send via Resend. Silently logs on missing key."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print(f"[Retention] RESEND_API_KEY not set — would send: {subject!r} → {to}")
        return

    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": "Quorint <onboarding@resend.dev>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        print(f"[Retention] Email sent: {subject!r} → {to}")
    except Exception as e:
        print(f"[Retention] Email send failed ({subject!r} → {to}): {e}")


def _record_trigger(db, report_id: str, trigger_type: str) -> None:
    db.table("retention_triggers").insert({
        "report_id": report_id,
        "trigger_type": trigger_type,
        "email_sent": True,
    }).execute()


def _get_active_reports(db) -> list[dict[str, Any]]:
    """All non-test completed reports, joined with manufacturer email via auth.users."""
    result = db.table("reports").select(
        "id, hs_code, origin_iso2, target_iso2, unit_cost_eur, tier, created_at, completed_at, "
        "manufacturers!inner(id, user_id, company)"
    ).eq("is_test", False).eq("status", "complete").execute()
    return result.data or []


def _get_user_email(db, user_id: str) -> Optional[str]:
    """Look up email from Supabase auth.users via admin API."""
    try:
        result = db.auth.admin.get_user_by_id(user_id)
        return result.user.email if result and result.user else None
    except Exception as e:
        print(f"[Retention] Could not fetch email for user {user_id}: {e}")
        return None


# ─────────────────────────────────────────
# Trigger 1 — Tariff change alert (weekly)
# ─────────────────────────────────────────

async def check_tariff_changes() -> None:
    """
    For each active completed report, check if the WITS tariff has changed
    since the report was generated. If it has, email the manufacturer.
    """
    print("[Retention] check_tariff_changes — starting")
    db = _supabase()
    reports = _get_active_reports(db)

    for report in reports:
        report_id = report["id"]
        hs_code = report["hs_code"]
        target_iso2 = report["target_iso2"]
        origin_iso2 = report["origin_iso2"]
        mfr = report.get("manufacturers") or {}
        user_id = mfr.get("user_id")
        company = mfr.get("company") or "your company"

        try:
            # Fetch stored tariff from report_demand
            demand_result = db.table("report_demand").select(
                "tariff_mfn, tariff_preferential"
            ).eq("report_id", report_id).execute()

            if not demand_result.data:
                continue

            stored = demand_result.data[0]
            stored_mfn = stored.get("tariff_mfn")

            # Fetch current tariff from WITS
            from data.wits import fetch_tariff
            current = await fetch_tariff(hs_code=hs_code, origin=origin_iso2, target=target_iso2)
            current_mfn = current.get("tariff_mfn")

            if current_mfn is None or stored_mfn is None:
                continue

            # Trigger only if rate changed by more than 0.1 percentage points
            if abs(float(current_mfn) - float(stored_mfn)) < 0.001:
                continue

            direction = "increased" if float(current_mfn) > float(stored_mfn) else "decreased"
            old_pct = round(float(stored_mfn) * 100, 1)
            new_pct = round(float(current_mfn) * 100, 1)

            email = _get_user_email(db, user_id) if user_id else None
            if not email:
                continue

            subject = f"Your {target_iso2} tariff position changed — update your margin"
            html = _tariff_email_html(
                company=company,
                hs_code=hs_code,
                target_iso2=target_iso2,
                old_pct=old_pct,
                new_pct=new_pct,
                direction=direction,
                report_id=report_id,
            )
            _send_email(email, subject, html)
            _record_trigger(db, report_id, "tariff_change")

            # Update stored tariff so we don't re-trigger on same change
            db.table("report_demand").update({
                "tariff_mfn": current_mfn,
                "tariff_preferential": current.get("tariff_preferential"),
            }).eq("report_id", report_id).execute()

        except Exception as e:
            print(f"[Retention] check_tariff_changes error for report {report_id}: {e}")

    print(f"[Retention] check_tariff_changes — processed {len(reports)} reports")


def _tariff_email_html(
    company: str,
    hs_code: str,
    target_iso2: str,
    old_pct: float,
    new_pct: float,
    direction: str,
    report_id: str,
) -> str:
    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "https://quorint.com")
    return f"""
<p>Hi {company},</p>

<p>The import tariff for <strong>HS {hs_code}</strong> into <strong>{target_iso2}</strong>
has <strong>{direction}</strong> since your report was generated.</p>

<ul>
  <li>Previous tariff: <strong>{old_pct}%</strong></li>
  <li>Current tariff: <strong>{new_pct}%</strong></li>
</ul>

<p>This affects your landed cost calculation and margin.
<a href="{app_url}/reports/{report_id}">Log in to see the updated margin</a>
— or upgrade to Copilot for automatic monthly tracking.</p>

<p>— Quorint</p>
"""


# ─────────────────────────────────────────
# Trigger 2 — New buyer signal (monthly)
# ─────────────────────────────────────────

async def check_new_buyers() -> None:
    """
    For each active completed report, run an abbreviated Apollo search
    (no scoring) and check if new companies have appeared since the last
    buyer list was stored. If so, email the manufacturer.
    """
    print("[Retention] check_new_buyers — starting")
    db = _supabase()
    reports = _get_active_reports(db)

    for report in reports:
        report_id = report["id"]
        hs_code = report["hs_code"]
        target_iso2 = report["target_iso2"]
        mfr = report.get("manufacturers") or {}
        user_id = mfr.get("user_id")
        company = mfr.get("company") or "your company"

        try:
            # Fetch existing buyer companies for this report
            existing = db.table("report_buyers").select("company_domain, company_name").eq(
                "report_id", report_id
            ).execute()
            existing_domains = {
                r["company_domain"] for r in (existing.data or []) if r.get("company_domain")
            }

            # Run abbreviated Apollo discovery (no scoring, just fresh companies)
            from data.apollo import fetch_buyers
            from scoring.config_loader import load_sector_config, hs_chapter_to_sector

            chapter = hs_code[:2]
            sector_name = hs_chapter_to_sector(chapter)
            sector_config = load_sector_config(sector_name) if sector_name else None
            if not sector_config:
                continue

            raw_buyers = await fetch_buyers(
                target_iso2=target_iso2,
                sector_config=sector_config,
                limit=20,
            )

            new_buyers = [
                b for b in raw_buyers
                if b.get("domain") and b["domain"] not in existing_domains
            ]

            if not new_buyers:
                continue

            email = _get_user_email(db, user_id) if user_id else None
            if not email:
                continue

            subject = f"New {target_iso2} buyer found — {new_buyers[0].get('name', 'a distributor')}"
            html = _new_buyer_email_html(
                company=company,
                target_iso2=target_iso2,
                new_buyers=new_buyers[:3],
                report_id=report_id,
            )
            _send_email(email, subject, html)
            _record_trigger(db, report_id, "new_buyer")

        except Exception as e:
            print(f"[Retention] check_new_buyers error for report {report_id}: {e}")

    print(f"[Retention] check_new_buyers — processed {len(reports)} reports")


def _new_buyer_email_html(
    company: str,
    target_iso2: str,
    new_buyers: list[dict],
    report_id: str,
) -> str:
    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "https://quorint.com")
    buyer_lines = "".join(
        f"<li><strong>{b.get('name', 'Unknown')}</strong> — {b.get('city', target_iso2)}</li>"
        for b in new_buyers
    )
    count = len(new_buyers)
    return f"""
<p>Hi {company},</p>

<p>We found <strong>{count} new {'buyer' if count == 1 else 'buyers'}</strong>
in <strong>{target_iso2}</strong> that weren't in your original report:</p>

<ul>{buyer_lines}</ul>

<p><a href="{app_url}/reports/{report_id}">Log in to see their contact details
and add them to your outreach list.</a></p>

<p>— Quorint</p>
"""


# ─────────────────────────────────────────
# Trigger 3 — Day-30 re-engagement (daily)
# ─────────────────────────────────────────

async def day30_reengagement() -> None:
    """
    Find reports that are 30+ days old and have never received a day30 trigger.
    Send one re-engagement email per report (fires exactly once).
    """
    print("[Retention] day30_reengagement — starting")
    db = _supabase()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # Reports older than 30 days
    reports_result = db.table("reports").select(
        "id, hs_code, target_iso2, created_at, "
        "manufacturers!inner(user_id, company)"
    ).eq("is_test", False).eq("status", "complete").lt("created_at", cutoff).execute()

    reports = reports_result.data or []

    # IDs that already have a day30 trigger
    triggered_result = db.table("retention_triggers").select("report_id").eq(
        "trigger_type", "day30"
    ).execute()
    already_triggered = {r["report_id"] for r in (triggered_result.data or [])}

    pending = [r for r in reports if r["id"] not in already_triggered]

    for report in pending:
        report_id = report["id"]
        target_iso2 = report["target_iso2"]
        hs_code = report["hs_code"]
        mfr = report.get("manufacturers") or {}
        user_id = mfr.get("user_id")
        company = mfr.get("company") or "your company"

        try:
            email = _get_user_email(db, user_id) if user_id else None
            if not email:
                continue

            subject = f"It's been 30 days — have you sent the first email to {target_iso2} buyers?"
            html = _day30_email_html(
                company=company,
                target_iso2=target_iso2,
                hs_code=hs_code,
                report_id=report_id,
            )
            _send_email(email, subject, html)
            _record_trigger(db, report_id, "day30")

        except Exception as e:
            print(f"[Retention] day30_reengagement error for report {report_id}: {e}")

    print(f"[Retention] day30_reengagement — sent {len(pending)} emails")


def _day30_email_html(
    company: str,
    target_iso2: str,
    hs_code: str,
    report_id: str,
) -> str:
    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "https://quorint.com")
    return f"""
<p>Hi {company},</p>

<p>It's been 30 days since your Quorint report for <strong>{target_iso2}</strong>
(HS {hs_code}) was delivered.</p>

<p>Have you sent the first email to the buyers on your list?</p>

<p>If not, <a href="{app_url}/reports/{report_id}">click here</a> — your
personalised outreach email is ready to send, pre-filled with your product
details and the buyer's company name. It takes 5 minutes.</p>

<p>The manufacturers who act in the first 30 days get replies.
The ones who wait 60+ days are forgotten.</p>

<p>— Quorint</p>
"""
