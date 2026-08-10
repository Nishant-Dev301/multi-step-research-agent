from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.orchestrator import ResearchOrchestrator,ResearchReport 
from app.x402.payment import SpendPolicy
from app.future import history
from app.future.export import EXPORTERS

app = FastAPI(
    title="Multi-Step Research Agent",
    description="Orchestrator that decomposes a research query into tasks, "
                "settles x402 payments per step, and compiles a cited report.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Keeps the most recent report per query in memory so /research/export can
# serve it without re-running (and re-paying for) the whole pipeline.
_last_reports: dict[str, ResearchReport] = {}


class ResearchRequest(BaseModel):
    query: str
    max_per_call: float = 0.05
    max_per_session: float = 1.00


@app.get("/")
def serve_ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/research")
def research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(400, "query must not be empty")

    policy = SpendPolicy(
        max_per_call=req.max_per_call,
        max_per_session=req.max_per_session,
    )
    orchestrator = ResearchOrchestrator(policy=policy)
    report = orchestrator.run(req.query)

    # Cache for export, and log to history — both are pure additions that
    # don't touch the core orchestration/payment logic above.
    _last_reports[req.query] = report
    history.record(
        query=report.query,
        duration_seconds=report.duration_seconds,
        total_spent=report.payment_summary["total_spent"],
        sections_count=len(report.sections),
    )

    return {
        "query": report.query,
        "sections": [asdict(s) for s in report.sections],
        "all_sources": report.all_sources,
        "payment_summary": report.payment_summary,
        "duration_seconds": report.duration_seconds,
    }


@app.get("/research/export/{fmt}")
def export_report(fmt: str, query: str):
    """Download the most recently generated report for `query` as
    Markdown or plain text. Run /research for that query first."""
    if fmt not in EXPORTERS:
        raise HTTPException(400, f"unsupported format '{fmt}'. Use one of: {list(EXPORTERS)}")

    report = _last_reports.get(query)
    if report is None:
        raise HTTPException(404, "no report found for that exact query — run /research first")

    render_fn, media_type = EXPORTERS[fmt]
    return PlainTextResponse(render_fn(report), media_type=media_type)


@app.get("/history")
def get_history():
    """Recent research queries run in this server session (most recent first)."""
    return {"history": history.all_entries()}
