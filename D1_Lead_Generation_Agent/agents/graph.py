from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from .models import ICP, Lead, PipelineResult
from .discovery import discover
from .enrichment import enrich
from .dedup import deduplicate
from .scoring import score
from .exporter import write_csv, write_hubspot_csv
import json
from pathlib import Path


class AgentState(TypedDict, total=False):
    icp: ICP
    leads: list[Lead]
    discovered_count: int
    duplicates_removed: int
    skipped_urls: list[str]
    logs: list[str]
    unique_count: int
    qualified_count: int
    average_score: float


def discovery_node(state: AgentState):
    icp = state["icp"]
    leads, logs = discover(icp)

    # If live search is unavailable, use safe demo records.
    if not leads:
        mock_path = Path(__file__).resolve().parent.parent / "data" / "mock_leads.json"
        data = json.loads(mock_path.read_text(encoding="utf-8"))
        leads = [Lead(**item) for item in data][:icp.lead_count]
        logs.append("Using mock/sample data because live discovery is unavailable.")

    for idx, lead in enumerate(leads, 1):
        lead.lead_id = f"D1-{idx:04d}"

    return {
        "leads": leads,
        "discovered_count": len(leads),
        "logs": state.get("logs", []) + logs,
    }


def enrichment_node(state: AgentState):
    leads, skipped, logs = enrich(state["leads"], state["icp"])
    return {
        "leads": leads,
        "skipped_urls": state.get("skipped_urls", []) + skipped,
        "logs": state.get("logs", []) + logs,
    }


def dedup_node(state: AgentState):
    leads, duplicates = deduplicate(state["leads"])
    for lead in leads:
        lead.duplicate_status = "Unique"
    return {
        "leads": leads,
        "duplicates_removed": duplicates,
        "unique_count": len(leads),
        "logs": state.get("logs", []) + [
            f"Deduplication removed {duplicates} duplicate records."
        ],
    }


def scoring_node(state: AgentState):
    leads = score(state["leads"], state["icp"])
    leads = sorted(leads, key=lambda lead: lead.icp_score, reverse=True)
    qualified = sum(1 for lead in leads if lead.icp_score >= 60)
    avg = round(sum(lead.icp_score for lead in leads) / len(leads), 1) if leads else 0.0
    return {
        "leads": leads,
        "qualified_count": qualified,
        "average_score": avg,
        "logs": state.get("logs", []) + ["Scoring completed with transparent rubric."],
    }


def export_node(state: AgentState):
    write_csv(state["leads"])
    write_hubspot_csv(state["leads"])
    return {
        "logs": state.get("logs", []) + [
            "CSV and HubSpot-style CSV exports created."
        ]
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("discovery", discovery_node)
    graph.add_node("enrichment", enrichment_node)
    graph.add_node("deduplication", dedup_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("export", export_node)

    graph.add_edge(START, "discovery")
    graph.add_edge("discovery", "enrichment")
    graph.add_edge("enrichment", "deduplication")
    graph.add_edge("deduplication", "scoring")
    graph.add_edge("scoring", "export")
    graph.add_edge("export", END)

    return graph.compile()


def run_pipeline(icp: ICP) -> PipelineResult:
    app = build_graph()
    final_state = app.invoke({"icp": icp, "logs": [], "skipped_urls": []})
    return PipelineResult(
        leads=final_state.get("leads", []),
        discovered_count=final_state.get("discovered_count", 0),
        duplicates_removed=final_state.get("duplicates_removed", 0),
        unique_count=final_state.get("unique_count", 0),
        qualified_count=final_state.get("qualified_count", 0),
        average_score=final_state.get("average_score", 0.0),
        skipped_urls=final_state.get("skipped_urls", []),
        logs=final_state.get("logs", []),
    )
