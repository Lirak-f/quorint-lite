"""LangGraph state schema and graph definition for the Quorint pipeline."""

from __future__ import annotations

from typing import Annotated, Any, Optional
import operator

from langgraph.graph import StateGraph, END

from models import (
    BuyerList,
    ComplianceOutput,
    DeepResearchOutput,
    DemandOutput,
    ManufacturerInput,
    ReportSynthesis,
)


class PipelineState(dict):
    """
    Typed dict used as LangGraph state.
    Each worker reads from and writes to this shared state object.
    """
    # Input
    report_id: str
    manufacturer: ManufacturerInput
    tier: str
    is_test: bool

    # Worker outputs (None until the worker completes)
    demand_output: Optional[DemandOutput]
    compliance_output: Optional[ComplianceOutput]
    buyer_list: Optional[BuyerList]
    deep_research_output: Optional[DeepResearchOutput]
    synthesis_output: Optional[ReportSynthesis]

    # Progress tracking
    current_worker: int          # 0–5 (0 = not started, 5 = done)
    error_message: Optional[str]
    status: str                  # queued | running | complete | failed


def _make_initial_state(
    report_id: str,
    manufacturer: ManufacturerInput,
    tier: str = "full",
    is_test: bool = False,
) -> PipelineState:
    return PipelineState(
        report_id=report_id,
        manufacturer=manufacturer,
        tier=tier,
        is_test=is_test,
        demand_output=None,
        compliance_output=None,
        buyer_list=None,
        deep_research_output=None,
        synthesis_output=None,
        current_worker=0,
        error_message=None,
        status="running",
    )


# ─────────────────────────────────────────
# Node functions — one per worker
# These are thin wrappers; actual logic lives in workers/
# ─────────────────────────────────────────

def node_w1_market(state: PipelineState) -> PipelineState:
    from workers.market_demand import run_market_demand
    m = state["manufacturer"]
    output = run_market_demand(
        hs_code=m.hs_code,
        origin_iso2=m.origin_iso2,
        target_iso2=m.target_iso2,
        unit_cost_eur=m.unit_cost_eur,
    )
    return {**state, "demand_output": output, "current_worker": 1}


def node_w2_compliance(state: PipelineState) -> PipelineState:
    # Compliance map disabled — skip LLM call, return empty output
    empty = ComplianceOutput(items=[], total_cost_low_eur=0, total_cost_high_eur=0)
    return {**state, "compliance_output": empty, "current_worker": 2}


def node_w3_buyers(state: PipelineState) -> PipelineState:
    from workers.buyers import run_buyers
    m = state["manufacturer"]
    output = run_buyers(
        hs_code=m.hs_code,
        origin_iso2=m.origin_iso2,
        target_iso2=m.target_iso2,
        manufacturer=m,
    )
    return {**state, "buyer_list": output, "current_worker": 3}


def node_w4_deep_research(state: PipelineState) -> PipelineState:
    from workers.deep_research import run_deep_research
    m = state["manufacturer"]
    output = run_deep_research(
        hs_code=m.hs_code,
        origin_iso2=m.origin_iso2,
        target_iso2=m.target_iso2,
    )
    return {**state, "deep_research_output": output, "current_worker": 4}


def node_w5_synthesis(state: PipelineState) -> PipelineState:
    from workers.synthesis import run_synthesis
    m = state["manufacturer"]
    output = run_synthesis(
        manufacturer=m,
        demand=state["demand_output"],
        compliance=state["compliance_output"],
        buyer_list=state["buyer_list"],
        deep_research=state["deep_research_output"],
        tier=state["tier"],
    )
    return {**state, "synthesis_output": output, "current_worker": 5, "status": "complete"}


def build_pipeline_graph() -> Any:
    """Build and compile the LangGraph pipeline."""
    graph = StateGraph(dict)

    graph.add_node("w1_market", node_w1_market)
    graph.add_node("w2_compliance", node_w2_compliance)
    graph.add_node("w3_buyers", node_w3_buyers)
    graph.add_node("w4_deep_research", node_w4_deep_research)
    graph.add_node("w5_synthesis", node_w5_synthesis)

    # Linear sequence: w1 → w2 → w3 → w4 → w5 → END
    graph.set_entry_point("w1_market")
    graph.add_edge("w1_market", "w2_compliance")
    graph.add_edge("w2_compliance", "w3_buyers")
    graph.add_edge("w3_buyers", "w4_deep_research")
    graph.add_edge("w4_deep_research", "w5_synthesis")
    graph.add_edge("w5_synthesis", END)

    return graph.compile()
