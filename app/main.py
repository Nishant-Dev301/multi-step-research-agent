from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.orchestrator import ResearchOrchestrator
from app.x402.payment import SpendPolicy

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

    return {
        "query": report.query,
        "sections": [asdict(s) for s in report.sections],
        "all_sources": report.all_sources,
        "payment_summary": report.payment_summary,
        "duration_seconds": report.duration_seconds,
    }
