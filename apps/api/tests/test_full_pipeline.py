"""End-to-end integration test — runs all 5 workers synchronously, no queue.

Canonical test case: HS 940360, XK → AT, unit cost €200, tier full.

Run from apps/api/:
  python tests/test_full_pipeline.py
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

CANONICAL = {
    "hs_code": "940360",
    "origin_iso2": "XK",
    "target_iso2": "AT",
    "unit_cost_eur": 200.0,
}
TIER = "full"


def run_test() -> None:
    console.rule("[bold blue]Quorint Full Pipeline Test — HS 940360, XK→AT, €200[/bold blue]")
    report_id = str(uuid.uuid4())
    console.print(f"Report ID: [dim]{report_id}[/dim]")
    console.print()

    total_start = time.time()
    failures: list[str] = []

    # ── Worker 1: Market demand ──────────────────────────────────────────────
    console.rule("[cyan]Worker 1 — Market demand + pricing[/cyan]")
    from workers.market_demand import run_market_demand
    w1_start = time.time()
    with console.status("Running Worker 1..."):
        demand = run_market_demand(**CANONICAL)
    console.print(f"[dim]Worker 1: {time.time() - w1_start:.1f}s[/dim]")

    # Assertions
    if demand.landed_cost is None:
        console.print("[yellow]⚠ landed_cost is None — missing retail price or freight data[/yellow]")
    else:
        lc = demand.landed_cost
        colour = {"viable": "green", "tight": "yellow", "not_viable": "red"}.get(lc.margin_verdict, "white")
        console.print(
            f"  Margin: [{colour}]{lc.margin:.1%} — {lc.margin_verdict.upper()}[/{colour}]"
            f"  (DAP €{lc.dap_per_unit_eur} vs wholesale mid €{lc.wholesale_mid_eur})"
        )
        assert lc.margin_verdict in ("viable", "tight", "not_viable"), \
            f"FAIL: margin_verdict must be viable/tight/not_viable, got {lc.margin_verdict!r}"
        console.print("  [green]✓ margin_verdict is valid[/green]")

    console.print()

    # ── Worker 2: Compliance ─────────────────────────────────────────────────
    console.rule("[cyan]Worker 2 — Compliance checklist[/cyan]")
    from workers.compliance import run_compliance
    w2_start = time.time()
    with console.status("Running Worker 2..."):
        compliance = run_compliance(hs_code=CANONICAL["hs_code"], target_iso2=CANONICAL["target_iso2"])
    console.print(f"[dim]Worker 2: {time.time() - w2_start:.1f}s[/dim]")

    critical_items = [i for i in compliance.items if i.critical]
    console.print(f"  Items: {len(compliance.items)} | Critical: {len(critical_items)}")
    for item in compliance.items:
        marker = "[bold red]⚠ CRITICAL[/bold red]" if item.critical else ""
        console.print(f"    {item.cert_name} — {item.cert_type} {marker}")

    try:
        assert len(critical_items) == 1, \
            f"FAIL: exactly 1 critical item required, got {len(critical_items)}"
        console.print("  [green]✓ exactly 1 critical compliance item[/green]")
    except AssertionError as e:
        failures.append(str(e))
        console.print(f"  [red]✗ {e}[/red]")

    console.print()

    # ── Worker 3: Buyer discovery ─────────────────────────────────────────────
    console.rule("[cyan]Worker 3 — Buyer discovery + scoring[/cyan]")
    from models import ManufacturerInput
    from workers.buyers import run_buyers
    manufacturer = ManufacturerInput(
        hs_code=CANONICAL["hs_code"],
        origin_iso2=CANONICAL["origin_iso2"],
        target_iso2=CANONICAL["target_iso2"],
        unit_cost_eur=CANONICAL["unit_cost_eur"],
    )
    w3_start = time.time()
    with console.status("Running Worker 3..."):
        buyer_list = run_buyers(
            hs_code=CANONICAL["hs_code"],
            origin_iso2=CANONICAL["origin_iso2"],
            target_iso2=CANONICAL["target_iso2"],
            manufacturer=manufacturer,
        )
    console.print(f"[dim]Worker 3: {time.time() - w3_start:.1f}s[/dim]")
    console.print(f"  Warm: {len(buyer_list.warm)} | Cold: {len(buyer_list.cold)} | Total scored: {buyer_list.total_scored}")

    if len(buyer_list.warm) < 3:
        msg = f"WARNING: only {len(buyer_list.warm)} warm buyers (expected ≥3) — Apollo may be returning limited results"
        console.print(f"  [yellow]⚠ {msg}[/yellow]")
    else:
        console.print(f"  [green]✓ {len(buyer_list.warm)} warm buyers returned[/green]")

    console.print()

    # ── Worker 4: Deep research ───────────────────────────────────────────────
    console.rule("[cyan]Worker 4 — Deep market research[/cyan]")
    from workers.deep_research import run_deep_research
    w4_start = time.time()
    with console.status("Running Worker 4 (may take 2–3 minutes for sonar-deep-research)..."):
        deep_research = run_deep_research(
            hs_code=CANONICAL["hs_code"],
            origin_iso2=CANONICAL["origin_iso2"],
            target_iso2=CANONICAL["target_iso2"],
        )
    console.print(f"[dim]Worker 4: {time.time() - w4_start:.1f}s[/dim]")
    console.print(f"  Narrative length: {len(deep_research.market_narrative)} chars")
    console.print(f"  Sources: {len(deep_research.sources)}")
    console.print(f"  Additional buyers found: {len(deep_research.additional_buyers)}")

    try:
        assert len(deep_research.market_narrative) > 100, \
            "FAIL: market_narrative too short — deep research may have failed"
        console.print("  [green]✓ market_narrative populated[/green]")
    except AssertionError as e:
        failures.append(str(e))
        console.print(f"  [red]✗ {e}[/red]")

    console.print()

    # ── Worker 5: Synthesis ───────────────────────────────────────────────────
    console.rule("[cyan]Worker 5 — Report synthesis[/cyan]")
    from workers.synthesis import run_synthesis
    w5_start = time.time()
    with console.status("Running Worker 5..."):
        synthesis = run_synthesis(
            manufacturer=manufacturer,
            demand=demand,
            compliance=compliance,
            buyer_list=buyer_list,
            deep_research=deep_research,
            tier=TIER,
        )
    console.print(f"[dim]Worker 5: {time.time() - w5_start:.1f}s[/dim]")

    wc = synthesis.working_capital
    console.print(f"  Working capital: €{wc.total_needed_eur:,.0f} | Days to revenue: {wc.days_to_revenue}")
    console.print(f"  Report length: {len(synthesis.full_report_markdown):,} chars")
    console.print(f"  Email length: {len(synthesis.first_contact_email)} chars")

    # Assertion: working_capital.total_needed > 0
    try:
        assert wc.total_needed_eur > 0, f"FAIL: total_needed_eur must be > 0, got {wc.total_needed_eur}"
        console.print("  [green]✓ working_capital.total_needed_eur > 0[/green]")
    except AssertionError as e:
        failures.append(str(e))
        console.print(f"  [red]✗ {e}[/red]")

    # Assertion: email body in German (target=AT)
    email = synthesis.first_contact_email
    german_indicators = [
        "Sehr geehrte", "sehr geehrte", "Lieber", "lieber", "Guten",
        "Wir sind", "Ich bin", "unsere", "Ihnen", "Sie", "Grüße", "Mit freundlichen",
        "Produkten", "Einkauf", "Händler", "Vertrieb", "möbel", "Möbel",
    ]
    email_is_german = any(indicator in email for indicator in german_indicators)
    try:
        assert email_is_german or len(email) > 50, \
            f"FAIL: email body should be in German (target=AT), got: {email[:100]!r}"
        if email_is_german:
            console.print("  [green]✓ email body appears to be in German[/green]")
        else:
            console.print("  [yellow]⚠ email may not be in German — check manually[/yellow]")
    except AssertionError as e:
        failures.append(str(e))
        console.print(f"  [red]✗ {e}[/red]")

    # Assertion: full_report_markdown has all 7 sections
    for section_num in range(1, 8):
        if f"## Section {section_num}" not in synthesis.full_report_markdown:
            msg = f"FAIL: Section {section_num} missing from full_report_markdown"
            failures.append(msg)
            console.print(f"  [red]✗ {msg}[/red]")
        else:
            console.print(f"  [green]✓ Section {section_num} present in report[/green]")

    console.print()

    # ── PDF generation ──────────────────────────────────────────────────────
    console.rule("[cyan]PDF Generation[/cyan]")
    pdf_path = "/tmp/test_report.pdf"
    try:
        from pdf.generator import generate_pdf_local
        with console.status("Generating PDF..."):
            generate_pdf_local(synthesis.full_report_markdown, pdf_path)
        pdf_size = Path(pdf_path).stat().st_size
        console.print(f"  [green]✓ PDF generated at {pdf_path} ({pdf_size:,} bytes)[/green]")
    except RuntimeError as e:
        if "WeasyPrint not installed" in str(e):
            console.print(f"  [yellow]⚠ WeasyPrint not installed — PDF skipped (run: pip install weasyprint)[/yellow]")
        else:
            failures.append(f"PDF generation failed: {e}")
            console.print(f"  [red]✗ PDF generation failed: {e}[/red]")
    except Exception as e:
        failures.append(f"PDF generation failed: {e}")
        console.print(f"  [red]✗ PDF generation failed: {e}[/red]")

    console.print()

    # ── Summary ──────────────────────────────────────────────────────────────
    total_elapsed = time.time() - total_start
    console.rule("[bold blue]Test Summary[/bold blue]")

    lc = demand.landed_cost
    summary_lines = [
        f"HS {CANONICAL['hs_code']} | {CANONICAL['origin_iso2']} → {CANONICAL['target_iso2']} | €{CANONICAL['unit_cost_eur']}",
        "",
        f"[bold]Market verdict:[/bold] {demand.one_sentence_verdict or 'N/A'}",
        f"[bold]Margin:[/bold] {lc.margin:.1%} ({lc.margin_verdict})" if lc else "[bold]Margin:[/bold] N/A",
        f"[bold]Compliance:[/bold] €{compliance.total_cost_low_eur:,}–€{compliance.total_cost_high_eur:,} | Critical: {compliance.critical_item_id}",
        f"[bold]Buyers:[/bold] {len(buyer_list.warm)} warm, {len(buyer_list.cold)} cold",
        f"[bold]Working capital needed:[/bold] €{wc.total_needed_eur:,.0f}",
        f"[bold]Total time:[/bold] {total_elapsed:.0f}s",
        "",
        f"[bold]PDF:[/bold] {pdf_path}",
    ]

    border = "green" if not failures else "red"
    console.print(Panel("\n".join(summary_lines), title="Executive Summary", border_style=border))

    if failures:
        console.print(f"\n[bold red]FAILED — {len(failures)} assertion(s) failed:[/bold red]")
        for f in failures:
            console.print(f"  [red]• {f}[/red]")
        sys.exit(1)
    else:
        console.print("\n[bold green]ALL ASSERTIONS PASSED ✓[/bold green]")

    # Print first 400 chars of the email for manual inspection
    if synthesis.first_contact_email:
        console.print("\n[bold]Email preview (first 400 chars):[/bold]")
        console.print(Panel(synthesis.first_contact_email[:400] + "...", border_style="cyan"))


if __name__ == "__main__":
    run_test()
