"""
Query Planner — decomposes a research query into an ordered task list.

Two modes:
  - "heuristic": deterministic rule-based split (no external API key needed —
    this is what runs by default so the demo works out of the box).
  - "llm": delegates decomposition to an LLM if OPENAI_API_KEY /
    ANTHROPIC_API_KEY is set. Drop-in — see llm_client.py.

Keeping heuristic mode as the default means the whole pipeline is runnable
and demoable with zero external dependencies or keys.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    id: str
    type: str        # "search" | "enrich" | "fact_check" | "summarize"
    query: str
    merchant: str     # which paid API/tool this task will call
    est_cost: float   # simulated x402 cost for this call


def plan(query: str) -> list[Task]:
    """
    Deterministic decomposition: every research query goes through the same
    four specialized stages, each parameterized by the original query.
    This mirrors the problem statement's required capabilities:
    search, summarization, fact-checking, data enrichment.
    """
    query = query.strip()
    return [
        Task(id="t1", type="search", query=query,
             merchant="search-api", est_cost=0.01),
        Task(id="t2", type="enrich", query=query,
             merchant="enrichment-api", est_cost=0.015),
        Task(id="t3", type="fact_check", query=query,
             merchant="factcheck-api", est_cost=0.02),
        Task(id="t4", type="summarize", query=query,
             merchant="summarizer-api", est_cost=0.01),
    ]
