"""CLI test tool — runs workers directly without queue or Paddle.

Usage:
  python test_report.py --hs 940360 --origin XK --target AT --cost 200
  python test_report.py --hs 940360 --origin XK --target AT --cost 200 --workers 1,2
  python test_report.py --hs 940360 --origin XK --target AT --cost 200 --workers 1,2,3 --verbose
  python test_report.py --hs 620520 --origin AL --target IT --cost 15 --pdf
  python test_report.py --hs 870899 --origin RS --target DE --cost 85
  python test_report.py --hs 150910 --origin MK --target DE --cost 3.50
"""

import argparse
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

VERDICT_COLOURS = {
    "viable": "bold green",
    "tight": "bold yellow",
    "not_viable": "bold red",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quorint report CLI — runs workers synchronously for testing"
    )
    parser.add_argument("--hs", required=True, help="HS code (4 or 6 digits)")
    parser.add_argument(
        "--origin",
        required=True,
        choices=["XK", "AL", "RS", "BA", "MK", "ME"],
        help="Origin country ISO-2",
    )
    parser.add_argument("--target", required=True, help="Target country ISO-2")
    parser.add_argument("--cost", required=True, type=float, help="Unit production cost in EUR")
    parser.add_argument("--pdf", action="store_true", help="Generate PDF (not yet implemented)")
    parser.add_argument("--verbose", action="store_true", help="Print full JSON output for each worker")
    parser.add_argument(
        "--tier",
        choices=["starter", "full"],
        default="full",
        help="Report tier (default: full)",
    )
    parser.add_argument(
        "--workers",
        default=None,
        help="Comma-separated worker numbers to run, e.g. 1,2,3 (default: all available)",
    )
    return parser.parse_args()


def parse_worker_set(workers_str: str | None) -> set[int]:
    """Parse --workers flag into a set of ints. None → all 5 workers."""
    if workers_str is None:
        return {1, 2, 3, 4, 5}
    try:
        return {int(w.strip()) for w in workers_str.split(",")}
    except ValueError:
        console.print("[bold red]Invalid --workers value. Use comma-separated integers, e.g. 1,2,3[/bold red]")
        sys.exit(1)


# ─────────────────────────────────────────
# Worker 1 output rendering
# ─────────────────────────────────────────

def print_demand_output(output, verbose: bool = False) -> None:
    """Render DemandOutput to the terminal using rich."""

    table = Table(title="[bold]Worker 1 — Market Demand Snapshot[/bold]", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim", width=34)
    table.add_column("Value")

    def fmt(val, fmt_str="{}", fallback="N/A"):
        return fmt_str.format(val) if val is not None else fallback

    table.add_row("Import value (latest year)", fmt(output.import_value_usd, "${:,.0f}"))
    table.add_row("5-year CAGR", fmt(output.cagr_5yr, "{:.1%}"))
    table.add_row("MFN tariff", fmt(output.tariff_mfn, "{:.1%}"))
    table.add_row("Preferential tariff", fmt(output.tariff_preferential, "{:.1%}"))
    table.add_row("Trade agreement", fmt(output.trade_agreement))
    table.add_row("RCA score", fmt(output.rca_score, "{:.2f}"))
    table.add_row("Target GDP (USD)", fmt(output.gdp_usd, "${:,.0f}"))
    table.add_row("Logistics Performance Index", fmt(output.lpi_score, "{:.2f}"))
    console.print(table)

    if output.retail_p25_eur is not None:
        price_table = Table(title="Price Reality Check", header_style="bold cyan")
        price_table.add_column("Level", style="dim")
        price_table.add_column("Retail (EUR)")
        price_table.add_column("Wholesale (EUR)")
        price_table.add_row(
            "P25 (low)",
            f"€{output.retail_p25_eur:,.2f}",
            f"€{output.wholesale_low_eur:,.2f}" if output.wholesale_low_eur else "N/A",
        )
        price_table.add_row("Median", f"€{output.retail_median_eur:,.2f}", "—")
        price_table.add_row(
            "P75 (high)",
            f"€{output.retail_p75_eur:,.2f}",
            f"€{output.wholesale_high_eur:,.2f}" if output.wholesale_high_eur else "N/A",
        )
        console.print(price_table)

    lc = output.landed_cost
    if lc:
        verdict_style = VERDICT_COLOURS.get(lc.margin_verdict, "white")
        lc_table = Table(title="Landed Cost Breakdown", header_style="bold cyan")
        lc_table.add_column("Item", style="dim")
        lc_table.add_column("Per unit (EUR)")
        lc_table.add_row("Production cost", f"€{lc.unit_cost_eur:,.2f}")
        lc_table.add_row(f"Freight ({lc.units_per_truck} units/truck)", f"€{lc.freight_per_unit_eur:,.2f}")
        lc_table.add_row("Customs + docs", f"€{lc.customs_per_unit_eur:,.2f}")
        lc_table.add_row("Insurance", f"€{lc.insurance_per_unit_eur:,.2f}")
        lc_table.add_row("[bold]DAP (delivered at place)[/bold]", f"[bold]€{lc.dap_per_unit_eur:,.2f}[/bold]")
        lc_table.add_row("Wholesale mid", f"€{lc.wholesale_mid_eur:,.2f}")
        lc_table.add_row(
            "Margin",
            Text(f"{lc.margin:.1%}  [{lc.margin_verdict.upper()}]", style=verdict_style),
        )
        console.print(lc_table)

    if output.fx_volatility_90d is not None:
        console.print(f"[yellow]FX volatility (90d): ±{output.fx_volatility_90d:.1%}[/yellow]")

    if output.top_suppliers:
        console.print("\n[bold cyan]Top Suppliers[/bold cyan]")
        for s in output.top_suppliers:
            console.print(f"  {s.country}: {s.share:.1%}")

    if output.competitor_summary:
        console.print(Panel(output.competitor_summary, title="Competitor Landscape", border_style="dim"))

    if output.demand_narrative:
        console.print(Panel(output.demand_narrative, title="Market Analysis", border_style="green"))

    if output.one_sentence_verdict:
        console.print(Panel(f"[bold]{output.one_sentence_verdict}[/bold]", title="Verdict", border_style="green"))

    if verbose:
        console.print("\n[dim]── Worker 1 Full JSON ──[/dim]")
        console.print_json(output.model_dump_json(indent=2))


# ─────────────────────────────────────────
# Worker 2 output rendering
# ─────────────────────────────────────────

def print_compliance_output(output, verbose: bool = False) -> None:
    """Render ComplianceOutput to the terminal."""
    table = Table(
        title="[bold]Worker 2 — Compliance Checklist[/bold]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Cert", style="dim", width=30)
    table.add_column("Type", width=18)
    table.add_column("Cost (EUR)")
    table.add_column("Lead time")
    table.add_column("Critical")

    for item in output.items:
        critical_mark = "[bold red]⚠ CRITICAL[/bold red]" if item.critical else ""
        table.add_row(
            item.cert_name,
            item.cert_type,
            f"€{item.cost_low_eur:,}–€{item.cost_high_eur:,}",
            f"{item.lead_time_min}–{item.lead_time_max} wks",
            critical_mark,
        )

    console.print(table)
    console.print(
        f"Total compliance cost: [bold]€{output.total_cost_low_eur:,}–€{output.total_cost_high_eur:,}[/bold]"
    )

    # Print notes for each item
    for item in output.items:
        if item.note:
            prefix = "[red]⚠[/red] " if item.critical else "  "
            console.print(f"{prefix}[bold]{item.cert_name}:[/bold] {item.note}")
            if item.providers:
                console.print(f"    Providers: {', '.join(item.providers[:2])}")

    if verbose:
        console.print("\n[dim]── Worker 2 Full JSON ──[/dim]")
        console.print_json(output.model_dump_json(indent=2))


# ─────────────────────────────────────────
# Worker 3 output rendering
# ─────────────────────────────────────────

def print_buyer_output(output, verbose: bool = False) -> None:
    """Render BuyerList to the terminal."""
    console.print(f"\n[bold]Worker 3 — Buyer Shortlist[/bold]  (scored: {output.total_scored})")

    if output.warm:
        warm_table = Table(title="[bold green]Warm Buyers (score ≥ 70)[/bold green]", header_style="bold green")
        warm_table.add_column("Score", width=6)
        warm_table.add_column("Company", width=28)
        warm_table.add_column("Contact", width=22)
        warm_table.add_column("Email", width=30)
        warm_table.add_column("Signals")

        for b in output.warm:
            warm_table.add_row(
                str(b.receptiveness_score),
                b.company_name,
                f"{b.contact_name or '—'} / {b.contact_title or '—'}",
                b.contact_email or "—",
                str(len(b.receptiveness_signals)) + " signals",
            )
        console.print(warm_table)

        for b in output.warm:
            if b.receptiveness_signals:
                console.print(f"  [green]{b.company_name}[/green] ({b.receptiveness_score}):")
                for sig in b.receptiveness_signals:
                    console.print(f"    • {sig}")
    else:
        console.print("[yellow]No warm buyers found (score ≥ 70).[/yellow]")

    if output.cold:
        cold_table = Table(title="[yellow]Cold Buyers (score 40–69)[/yellow]", header_style="bold yellow")
        cold_table.add_column("Score", width=6)
        cold_table.add_column("Company", width=28)
        cold_table.add_column("Contact", width=22)
        cold_table.add_column("Source", width=10)

        for b in output.cold:
            cold_table.add_row(
                str(b.receptiveness_score),
                b.company_name,
                b.contact_name or "—",
                b.enrichment_source,
            )
        console.print(cold_table)

    if verbose:
        console.print("\n[dim]── Worker 3 Full JSON ──[/dim]")
        console.print_json(output.model_dump_json(indent=2))


# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────

def main() -> None:
    args = parse_args()
    workers_to_run = parse_worker_set(args.workers)

    import os
    from dotenv import load_dotenv
    load_dotenv()

    console.rule("[bold blue]Quorint CLI[/bold blue]")
    console.print(
        f"HS [bold]{args.hs}[/bold] | "
        f"[bold]{args.origin}[/bold] → [bold]{args.target}[/bold] | "
        f"Cost: [bold]€{args.cost}[/bold] | Tier: [bold]{args.tier}[/bold] | "
        f"Workers: [bold]{sorted(workers_to_run)}[/bold]"
    )

    from models import ManufacturerInput
    manufacturer = ManufacturerInput(
        hs_code=args.hs,
        origin_iso2=args.origin,
        target_iso2=args.target,
        unit_cost_eur=args.cost,
        tier=args.tier,
    )

    # Running state — set by each worker, used by downstream workers
    demand_output = None
    compliance_output = None
    buyer_output = None
    deep_research_output = None
    synthesis_output = None

    # ── Worker 1 ──────────────────────────────────────────────────────────
    if 1 in workers_to_run:
        from workers.market_demand import run_market_demand
        console.rule("[cyan]Worker 1 — Market demand + pricing[/cyan]")
        start = time.time()
        with console.status("[bold green]Running Worker 1..."):
            try:
                demand_output = run_market_demand(
                    hs_code=args.hs,
                    origin_iso2=args.origin,
                    target_iso2=args.target,
                    unit_cost_eur=args.cost,
                )
            except Exception as e:
                console.print(f"[bold red]Worker 1 failed:[/bold red] {e}")
                sys.exit(1)
        console.print(f"[dim]Worker 1 done in {time.time() - start:.1f}s[/dim]")
        print_demand_output(demand_output, verbose=args.verbose)

    # ── Worker 2 ──────────────────────────────────────────────────────────
    if 2 in workers_to_run:
        from workers.compliance import run_compliance
        console.rule("[cyan]Worker 2 — Compliance map[/cyan]")
        start = time.time()
        with console.status("[bold green]Running Worker 2..."):
            try:
                compliance_output = run_compliance(
                    hs_code=args.hs,
                    target_iso2=args.target,
                )
            except Exception as e:
                console.print(f"[bold red]Worker 2 failed:[/bold red] {e}")
                sys.exit(1)
        console.print(f"[dim]Worker 2 done in {time.time() - start:.1f}s[/dim]")
        print_compliance_output(compliance_output, verbose=args.verbose)

    # ── Worker 3 ──────────────────────────────────────────────────────────
    if 3 in workers_to_run:
        from workers.buyers import run_buyers
        console.rule("[cyan]Worker 3 — Buyer discovery + scoring[/cyan]")
        start = time.time()
        with console.status("[bold green]Running Worker 3..."):
            try:
                buyer_output = run_buyers(
                    hs_code=args.hs,
                    origin_iso2=args.origin,
                    target_iso2=args.target,
                    manufacturer=manufacturer,
                )
            except Exception as e:
                console.print(f"[bold red]Worker 3 failed:[/bold red] {e}")
                sys.exit(1)
        console.print(f"[dim]Worker 3 done in {time.time() - start:.1f}s[/dim]")
        print_buyer_output(buyer_output, verbose=args.verbose)

    # ── Worker 4 ──────────────────────────────────────────────────────────
    if 4 in workers_to_run:
        from workers.deep_research import run_deep_research
        console.rule("[cyan]Worker 4 — Deep market research[/cyan]")
        start = time.time()
        with console.status("[bold green]Running Worker 4 (Perplexity deep research ~2min)..."):
            try:
                deep_research_output = run_deep_research(
                    hs_code=args.hs,
                    origin_iso2=args.origin,
                    target_iso2=args.target,
                )
            except Exception as e:
                console.print(f"[bold red]Worker 4 failed:[/bold red] {e}")
                sys.exit(1)
        console.print(f"[dim]Worker 4 done in {time.time() - start:.1f}s[/dim]")
        if deep_research_output.market_narrative:
            excerpt = deep_research_output.market_narrative[:600]
            console.print(Panel(excerpt + "…", title="Worker 4 — Deep Research Excerpt", border_style="blue"))
        if deep_research_output.sources:
            console.print(f"[dim]{len(deep_research_output.sources)} sources cited[/dim]")
        if deep_research_output.additional_buyers:
            console.print(f"[dim]{len(deep_research_output.additional_buyers)} additional buyers extracted from narrative[/dim]")
    else:
        from models import DeepResearchOutput
        deep_research_output = DeepResearchOutput(market_narrative="", sources=[], additional_buyers=[])

    # ── Worker 5 ──────────────────────────────────────────────────────────
    if 5 in workers_to_run:
        if demand_output is None or compliance_output is None or buyer_output is None:
            console.print("[bold red]Worker 5 requires Workers 1, 2, 3 to have run first.[/bold red]")
            sys.exit(1)
        from workers.synthesis import run_synthesis
        console.rule("[cyan]Worker 5 — Report synthesis[/cyan]")
        start = time.time()
        with console.status("[bold green]Running Worker 5 (Claude synthesis)..."):
            try:
                synthesis_output = run_synthesis(
                    manufacturer=manufacturer,
                    demand=demand_output,
                    compliance=compliance_output,
                    buyer_list=buyer_output,
                    deep_research=deep_research_output,
                    tier=args.tier,
                )
            except Exception as e:
                console.print(f"[bold red]Worker 5 failed:[/bold red] {e}")
                sys.exit(1)
        console.print(f"[dim]Worker 5 done in {time.time() - start:.1f}s[/dim]")

        # Print working capital
        wc = synthesis_output.working_capital
        console.print(Panel(wc.plain_english, title="Working Capital Estimate", border_style="yellow"))

        # Print first contact email
        if synthesis_output.first_contact_email:
            console.print(Panel(
                synthesis_output.first_contact_email,
                title="Section 5 — First Contact Email",
                border_style="green",
            ))

        # Print action plan excerpt
        if synthesis_output.action_plan_markdown:
            console.print(Panel(
                synthesis_output.action_plan_markdown[:800],
                title="Section 6 — 90-Day Action Plan (excerpt)",
                border_style="cyan",
            ))

        # Print risk flags
        if synthesis_output.risk_flags_markdown:
            console.print(Panel(
                synthesis_output.risk_flags_markdown,
                title="Section 7 — Risk Flags",
                border_style="red",
            ))

        # Save full report markdown
        import os
        report_path = f"report_{args.hs}_{args.origin}_{args.target}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(synthesis_output.full_report_markdown)
        console.print(f"[green]Full report saved to:[/green] {report_path}")

        # Generate PDF if requested
        if args.pdf:
            _generate_pdf(synthesis_output.full_report_markdown, args.hs, args.origin, args.target, console)
    else:
        synthesis_output = None

    console.rule("[bold green]Done[/bold green]")


def _generate_pdf(
    markdown_content: str,
    hs_code: str,
    origin: str,
    target: str,
    console,
) -> None:
    """Convert report markdown to PDF using WeasyPrint."""
    try:
        import markdown
        from weasyprint import HTML, CSS

        html_body = markdown.markdown(
            markdown_content,
            extensions=["tables", "fenced_code"],
        )
        pdf_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 11px; line-height: 1.5; color: #222; max-width: 800px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 22px; color: #1a1a2e; border-bottom: 2px solid #e74c3c; padding-bottom: 8px; }}
  h2 {{ font-size: 17px; color: #1a1a2e; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 28px; }}
  h3 {{ font-size: 14px; color: #333; margin-top: 16px; }}
  h4 {{ font-size: 12px; color: #555; margin-top: 12px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10px; }}
  th {{ background: #1a1a2e; color: white; padding: 6px 8px; text-align: left; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #eee; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  blockquote {{ background: #fff8e7; border-left: 4px solid #f0a500; padding: 8px 12px; margin: 12px 0; font-size: 10px; }}
  code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; font-size: 9px; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
  @page {{ margin: 1.5cm 1.5cm 1.5cm 1.5cm; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

        pdf_path = f"report_{hs_code}_{origin}_{target}.pdf"
        HTML(string=pdf_html).write_pdf(pdf_path)
        console.print(f"[green]PDF generated:[/green] {pdf_path}")
    except ImportError as e:
        console.print(f"[yellow]PDF generation skipped — install weasyprint and markdown: {e}[/yellow]")
    except Exception as e:
        console.print(f"[red]PDF generation failed:[/red] {e}")


if __name__ == "__main__":
    main()
