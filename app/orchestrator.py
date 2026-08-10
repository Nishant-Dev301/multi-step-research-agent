"""
Orchestrator — the core of the Multi-Step Research Agent.

Flow per problem statement:
  1. Decompose the research query into tasks (planner.py)
  2. For each task: settle an x402 payment BEFORE invoking the tool
  3. Invoke the specialized tool/agent (tools.py)
  4. Compile all task outputs into one cited report

This is intentionally synchronous and sequential for clarity in a hackathon
demo — an easy next step is to parallelize independent tasks (search +
enrich can run concurrently) using asyncio.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.agents.planner import plan, Task
from app.agents.tools import TOOL_MERCHANT_MAP, ToolResult
from app.x402.payment import MockPaymentProvider, SpendPolicy, SpendPolicyError


@dataclass
class ReportSection:
    task_type: str
    content: str
    sources: list[str]
    confidence: float
    payment_status: str
    payment_amount: float


@dataclass
class ResearchReport:
    query: str
    sections: list[ReportSection]
    all_sources: list[str]
    payment_summary: dict
    duration_seconds: float


class ResearchOrchestrator:
    def __init__(self, policy: SpendPolicy | None = None):
        self.payment_provider = MockPaymentProvider(policy or SpendPolicy())

    def run(self, query: str) -> ResearchReport:
        start = time.time()
        tasks: list[Task] = plan(query)
        results: list[ToolResult] = []
        sections: list[ReportSection] = []

        for task in tasks:
            tool_fn = TOOL_MERCHANT_MAP[task.type]

            try:
                payment = self.payment_provider.pay(
                    merchant=task.merchant, amount=task.est_cost, task=task.type
                )
                payment_status, payment_amount = payment.status, payment.amount
            except SpendPolicyError as e:
                # Policy blocked this call — skip the tool, note it in the report
                sections.append(ReportSection(
                    task_type=task.type,
                    content=f"[Skipped: payment rejected — {e}]",
                    sources=[],
                    confidence=0.0,
                    payment_status="rejected",
                    payment_amount=task.est_cost,
                ))
                continue

            # Tools that build on prior context receive earlier results
            if task.type in ("enrich", "fact_check", "summarize"):
                result = tool_fn(task.query, results)
            else:
                result = tool_fn(task.query)

            results.append(result)
            sections.append(ReportSection(
                task_type=result.task_type,
                content=result.content,
                sources=result.sources,
                confidence=result.confidence,
                payment_status=payment_status,
                payment_amount=payment_amount,
            ))

        all_sources = sorted({s for sec in sections for s in sec.sources})
        duration = time.time() - start

        return ResearchReport(
            query=query,
            sections=sections,
            all_sources=all_sources,
            payment_summary=self.payment_provider.summary(),
            duration_seconds=round(duration, 3),
        )
