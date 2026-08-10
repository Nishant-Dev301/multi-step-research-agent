"""
Parallel orchestrator — advanced enhancement (see ENHANCEMENTS.md).

The base ResearchOrchestrator (app/orchestrator.py) runs every task
sequentially for clarity in the hackathon demo. `search` and `enrich` don't
actually depend on each other's output, so they can run concurrently.
`fact_check` and `summarize` still need to wait for earlier results, so
they stay sequential after the parallel group.

This is a drop-in alternative: same public API (`run(query) -> ResearchReport`)
as `ResearchOrchestrator`, so swapping it into `main.py` is a one-line change:

    from app.future.parallel_orchestrator import ParallelResearchOrchestrator
    orchestrator = ParallelResearchOrchestrator(policy=policy)

Status: runnable today (no external services needed, since tools are mocked).
Payment settlement still happens synchronously and in-order per task, since
policy checks (session budget) must be evaluated sequentially to stay correct
under a shared budget — only the tool *invocation* is parallelized.
"""

from __future__ import annotations

import asyncio
import time

from app.agents.planner import plan, Task
from app.agents.tools import TOOL_MERCHANT_MAP, ToolResult
from app.orchestrator import ReportSection, ResearchReport
from app.x402.payment import MockPaymentProvider, SpendPolicy, SpendPolicyError

# Tasks that have no dependency on prior results and are safe to run together.
PARALLELIZABLE = {"search"}
# Tasks that depend on results gathered so far and must run after the
# parallel group completes.
SEQUENTIAL_AFTER = {"enrich", "fact_check", "summarize"}


class ParallelResearchOrchestrator:
    def __init__(self, policy: SpendPolicy | None = None):
        self.payment_provider = MockPaymentProvider(policy or SpendPolicy())

    def _settle(self, task: Task) -> tuple[str, float, str | None]:
        """Synchronous payment settlement — must stay ordered for budget correctness."""
        try:
            payment = self.payment_provider.pay(
                merchant=task.merchant, amount=task.est_cost, task=task.type
            )
            return payment.status, payment.amount, None
        except SpendPolicyError as e:
            return "rejected", task.est_cost, str(e)

    async def _run_tool_async(self, task: Task, prior: list[ToolResult]) -> ToolResult:
        """Wraps a synchronous mock tool call so it can run inside asyncio.gather.
        Replace with a genuinely async HTTP call (httpx/aiohttp) once tools
        call real paid APIs."""
        loop = asyncio.get_event_loop()
        tool_fn = TOOL_MERCHANT_MAP[task.type]
        if task.type in SEQUENTIAL_AFTER:
            return await loop.run_in_executor(None, tool_fn, task.query, prior)
        return await loop.run_in_executor(None, tool_fn, task.query)

    async def _run_async(self, query: str) -> ResearchReport:
        start = time.time()
        tasks: list[Task] = plan(query)
        results: list[ToolResult] = []
        sections: list[ReportSection] = []

        parallel_group = [t for t in tasks if t.type in PARALLELIZABLE]
        sequential_group = [t for t in tasks if t.type in SEQUENTIAL_AFTER]

        # --- Phase 1: settle payments + run parallelizable tasks concurrently ---
        coros = []
        settle_info = []
        for task in parallel_group:
            status, amount, reason = self._settle(task)
            settle_info.append((task, status, amount, reason))
            if status == "settled":
                coros.append(self._run_tool_async(task, results))

        tool_results = await asyncio.gather(*coros) if coros else []
        tr_iter = iter(tool_results)

        for task, status, amount, reason in settle_info:
            if status == "settled":
                result = next(tr_iter)
                results.append(result)
                sections.append(ReportSection(
                    task_type=result.task_type, content=result.content,
                    sources=result.sources, confidence=result.confidence,
                    payment_status=status, payment_amount=amount,
                ))
            else:
                sections.append(ReportSection(
                    task_type=task.type, content=f"[Skipped: payment rejected — {reason}]",
                    sources=[], confidence=0.0,
                    payment_status="rejected", payment_amount=amount,
                ))

        # --- Phase 2: sequential tasks that depend on Phase 1 results ---
        for task in sequential_group:
            status, amount, reason = self._settle(task)
            if status != "settled":
                sections.append(ReportSection(
                    task_type=task.type, content=f"[Skipped: payment rejected — {reason}]",
                    sources=[], confidence=0.0,
                    payment_status="rejected", payment_amount=amount,
                ))
                continue
            result = await self._run_tool_async(task, results)
            results.append(result)
            sections.append(ReportSection(
                task_type=result.task_type, content=result.content,
                sources=result.sources, confidence=result.confidence,
                payment_status=status, payment_amount=amount,
            ))

        all_sources = sorted({s for sec in sections for s in sec.sources})
        return ResearchReport(
            query=query, sections=sections, all_sources=all_sources,
            payment_summary=self.payment_provider.summary(),
            duration_seconds=round(time.time() - start, 3),
        )

    def run(self, query: str) -> ResearchReport:
        """Synchronous entry point matching ResearchOrchestrator's API."""
        return asyncio.run(self._run_async(query))
