"""Worker 1 test script — canonical test case: XK → AT, HS 940360, cost €200.

Run from apps/api/:
  python tests/test_worker1.py

This is the first thing to run after setup to verify all APIs work.
"""

import json
import os
import sys
import time
from pathlib import Path

# Make sure apps/api is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv(Path(__file__).parent.parent / ".env")

console = Console()

CANONICAL = {
    "hs_code": "940360",
    "origin_iso2": "XK",
    "target_iso2": "AT",
    "unit_cost_eur": 200.0,
}


def main():
    console.rule("[bold blue]Worker 1 — Canonical Test[/bold blue]")
    console.print(
        f"Test case: HS [bold]{CANONICAL['hs_code']}[/bold] | "
        f"[bold]{CANONICAL['origin_iso2']}[/bold] → [bold]{CANONICAL['target_iso2']}[/bold] | "
        f"Cost: [bold]€{CANONICAL['unit_cost_eur']}[/bold]"
    )
    console.print()

    from workers.market_demand import run_market_demand

    start = time.time()
    with console.status("[bold green]Running Worker 1..."):
        output = run_market_demand(**CANONICAL)
    elapsed = time.time() - start

    console.print(f"[dim]Completed in {elapsed:.1f}s[/dim]\n")

    # Print full output as formatted JSON
    console.print(Panel(
        output.model_dump_json(indent=2),
        title="[bold cyan]DemandOutput — Full JSON[/bold cyan]",
        border_style="cyan",
    ))

    # Highlight the verdict
    if output.landed_cost:
        lc = output.landed_cost
        verdict_colour = {"viable": "green", "tight": "yellow", "not_viable": "red"}.get(
            lc.margin_verdict, "white"
        )
        console.print(Panel(
            f"DAP: €{lc.dap_per_unit_eur} | Wholesale mid: €{lc.wholesale_mid_eur}\n"
            f"Margin: {lc.margin:.1%} → [{verdict_colour}]{lc.margin_verdict.upper()}[/{verdict_colour}]",
            title="Margin Verdict",
            border_style=verdict_colour,
        ))
    else:
        console.print("[yellow]No landed cost calculated (missing freight or price data)[/yellow]")

    if output.one_sentence_verdict:
        console.print(Panel(
            f"[bold]{output.one_sentence_verdict}[/bold]",
            title="One-sentence Verdict",
            border_style="green",
        ))

    console.print("\n[bold green]Worker 1 test complete.[/bold green]")


if __name__ == "__main__":
    main()
