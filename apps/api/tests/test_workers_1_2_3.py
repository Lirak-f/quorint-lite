"""Integration test — runs Workers 1, 2, 3 sequentially.
Canonical test case: HS 940360, XK → AT, unit cost €200.

Run from apps/api/:
  python tests/test_workers_1_2_3.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

load_dotenv(Path(__file__).parent.parent / ".env")

console = Console()

CANONICAL = {
    "hs_code": "940360",
    "origin_iso2": "XK",
    "target_iso2": "AT",
    "unit_cost_eur": 200.0,
}

VERDICT_COLOURS = {
    "viable": "green",
    "tight": "yellow",
    "not_viable": "red",
}


def run_worker1():
    from workers.market_demand import run_market_demand
    console.rule("[cyan]Worker 1 — Market demand + pricing[/cyan]")
    start = time.time()
    with console.status("[bold green]Running Worker 1..."):
        output = run_market_demand(**CANONICAL)
    elapsed = time.time() - start
    console.print(f"[dim]Worker 1 completed in {elapsed:.1f}s[/dim]")

    # Demand snapshot
    t = Table(title="Market Demand Snapshot", header_style="bold cyan")
    t.add_column("Metric", style="dim", width=34)
    t.add_column("Value")

    def fmt(val, fmt_str="{}", fallback="N/A"):
        return fmt_str.format(val) if val is not None else fallback

    t.add_row("Import value (latest year)", fmt(output.import_value_usd, "${:,.0f}"))
    t.add_row("5-year CAGR", fmt(output.cagr_5yr, "{:.1%}"))
    t.add_row("Trade agreement (XK→AT)", fmt(output.trade_agreement))
    t.add_row("Preferential tariff", fmt(output.tariff_preferential, "{:.1%}"))
    t.add_row("RCA score", fmt(output.rca_score, "{:.2f}"))
    t.add_row("Target GDP", fmt(output.gdp_usd, "${:,.0f}"))
    t.add_row("Retail median (EUR)", fmt(output.retail_median_eur, "€{:,.0f}"))
    t.add_row("Wholesale low (EUR)", fmt(output.wholesale_low_eur, "€{:,.0f}"))
    console.print(t)

    lc = output.landed_cost
    if lc:
        colour = VERDICT_COLOURS.get(lc.margin_verdict, "white")
        console.print(Panel(
            f"DAP: €{lc.dap_per_unit_eur} | Wholesale mid: €{lc.wholesale_mid_eur}\n"
            f"Margin: {lc.margin:.1%} → [{colour}]{lc.margin_verdict.upper()}[/{colour}]",
            title="Margin Verdict",
            border_style=colour,
        ))
    else:
        console.print("[yellow]Landed cost: N/A (missing freight or price data)[/yellow]")

    if output.one_sentence_verdict:
        console.print(Panel(
            f"[bold]{output.one_sentence_verdict}[/bold]",
            title="One-sentence verdict",
            border_style="green",
        ))

    return output


def run_worker2():
    from workers.compliance import run_compliance
    console.rule("[cyan]Worker 2 — Compliance checklist[/cyan]")
    start = time.time()
    with console.status("[bold green]Running Worker 2..."):
        output = run_compliance(
            hs_code=CANONICAL["hs_code"],
            target_iso2=CANONICAL["target_iso2"],
        )
    elapsed = time.time() - start
    console.print(f"[dim]Worker 2 completed in {elapsed:.1f}s[/dim]")

    t = Table(title="Compliance Checklist", header_style="bold cyan")
    t.add_column("Cert", width=30)
    t.add_column("Type", width=18)
    t.add_column("Cost (EUR)")
    t.add_column("Lead time")
    t.add_column("")

    for item in output.items:
        crit = "[bold red]⚠ CRITICAL[/bold red]" if item.critical else ""
        t.add_row(
            item.cert_name,
            item.cert_type,
            f"€{item.cost_low_eur:,}–€{item.cost_high_eur:,}",
            f"{item.lead_time_min}–{item.lead_time_max} wks",
            crit,
        )
    console.print(t)

    console.print(
        f"Total: [bold]€{output.total_cost_low_eur:,}–€{output.total_cost_high_eur:,}[/bold]  |  "
        f"Critical item: [bold red]{output.critical_item_id or 'none flagged'}[/bold red]"
    )

    for item in output.items:
        if item.note:
            prefix = "[red]⚠[/red]" if item.critical else " "
            console.print(f"  {prefix} [bold]{item.cert_name}:[/bold] {item.note}")

    return output


def run_worker3():
    from models import ManufacturerInput
    from workers.buyers import run_buyers
    console.rule("[cyan]Worker 3 — Buyer discovery + receptiveness[/cyan]")

    manufacturer = ManufacturerInput(
        hs_code=CANONICAL["hs_code"],
        origin_iso2=CANONICAL["origin_iso2"],
        target_iso2=CANONICAL["target_iso2"],
        unit_cost_eur=CANONICAL["unit_cost_eur"],
    )

    start = time.time()
    with console.status("[bold green]Running Worker 3..."):
        output = run_buyers(
            hs_code=CANONICAL["hs_code"],
            origin_iso2=CANONICAL["origin_iso2"],
            target_iso2=CANONICAL["target_iso2"],
            manufacturer=manufacturer,
        )
    elapsed = time.time() - start
    console.print(f"[dim]Worker 3 completed in {elapsed:.1f}s[/dim]")

    console.print(f"Scored: {output.total_scored} buyers | Warm: {len(output.warm)} | Cold: {len(output.cold)}")

    if output.warm:
        wt = Table(title="[bold green]Warm Buyers (score ≥ 70)[/bold green]", header_style="bold green")
        wt.add_column("Score", width=6)
        wt.add_column("Company", width=28)
        wt.add_column("Contact", width=24)
        wt.add_column("Email", width=32)
        wt.add_column("Source", width=10)

        for b in output.warm:
            wt.add_row(
                str(b.receptiveness_score),
                b.company_name,
                f"{b.contact_name or '—'}\n{b.contact_title or '—'}",
                b.contact_email or "—",
                b.enrichment_source,
            )
        console.print(wt)

        console.print("\n[bold green]Warm buyer signals:[/bold green]")
        for b in output.warm:
            console.print(f"  [green]{b.company_name}[/green] (score {b.receptiveness_score}):")
            for sig in b.receptiveness_signals:
                console.print(f"    • {sig}")
    else:
        console.print("[yellow]No warm buyers found — this is expected if Apollo has no results for this query.[/yellow]")

    if output.cold:
        ct = Table(title="[yellow]Cold Buyers (score 40–69)[/yellow]", header_style="bold yellow")
        ct.add_column("Score", width=6)
        ct.add_column("Company", width=28)
        ct.add_column("Contact", width=22)
        ct.add_column("Source", width=10)
        for b in output.cold[:5]:  # show first 5
            ct.add_row(str(b.receptiveness_score), b.company_name, b.contact_name or "—", b.enrichment_source)
        console.print(ct)

    return output


def print_combined_summary(demand, compliance, buyers) -> None:
    console.rule("[bold blue]Combined Report Summary[/bold blue]")

    lc = demand.landed_cost
    if lc:
        colour = VERDICT_COLOURS.get(lc.margin_verdict, "white")
        verdict_text = Text(f"{lc.margin:.1%} margin — {lc.margin_verdict.upper()}", style=colour)
    else:
        verdict_text = Text("Margin data unavailable", style="yellow")

    critical = next((i for i in compliance.items if i.critical), None)
    critical_text = (
        f"[red]{critical.cert_name} ({critical.lead_time_min}–{critical.lead_time_max} wks)[/red]"
        if critical else "[dim]None flagged[/dim]"
    )

    lines = [
        f"HS {CANONICAL['hs_code']} | {CANONICAL['origin_iso2']} → {CANONICAL['target_iso2']}",
        "",
        f"[bold]Market:[/bold] {demand.one_sentence_verdict or 'N/A'}",
        f"[bold]Margin:[/bold] {verdict_text}",
        f"[bold]Compliance cost:[/bold] €{compliance.total_cost_low_eur:,}–€{compliance.total_cost_high_eur:,}",
        f"[bold]Critical compliance item:[/bold] {critical_text}",
        f"[bold]Warm buyers:[/bold] {len(buyers.warm)} / Cold: {len(buyers.cold)}",
    ]

    console.print(Panel("\n".join(lines), title="Executive Summary", border_style="blue"))


def main():
    console.rule("[bold blue]Workers 1 + 2 + 3 — Integration Test[/bold blue]")
    console.print(
        f"HS [bold]{CANONICAL['hs_code']}[/bold] | "
        f"[bold]{CANONICAL['origin_iso2']}[/bold] → [bold]{CANONICAL['target_iso2']}[/bold] | "
        f"Cost: [bold]€{CANONICAL['unit_cost_eur']}[/bold]"
    )
    console.print()

    total_start = time.time()

    demand = run_worker1()
    console.print()

    compliance = run_worker2()
    console.print()

    buyers = run_worker3()
    console.print()

    print_combined_summary(demand, compliance, buyers)

    total_elapsed = time.time() - total_start
    console.print(f"\n[dim]Total time: {total_elapsed:.1f}s[/dim]")
    console.print("[bold green]Integration test complete.[/bold green]")


if __name__ == "__main__":
    main()
