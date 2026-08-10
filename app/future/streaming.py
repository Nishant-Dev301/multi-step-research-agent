"""
Streaming responses (SSE) — advanced enhancement (see ENHANCEMENTS.md).

Status: 🟡 designed, not wired in. Requires restructuring the orchestrator
to yield each ReportSection as it completes rather than returning the full
ResearchReport at the end. Pairs well with a progress bar in the UI.

Sketch of the intended endpoint (add to main.py once orchestrator supports
a generator-based `run_streaming`):

    from fastapi.responses import StreamingResponse
    import json

    @app.get("/research/stream")
    async def research_stream(query: str):
        async def event_generator():
            orchestrator = ResearchOrchestrator(policy=SpendPolicy())
            async for section in orchestrator.run_streaming(query):
                yield f"data: {json.dumps(section.__dict__)}\n\n"
            yield "event: done\ndata: {}\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream")

Client side (index.html) would consume this with:

    const es = new EventSource(`/research/stream?query=${encodeURIComponent(q)}`);
    es.onmessage = (e) => appendSection(JSON.parse(e.data));
    es.addEventListener("done", () => es.close());
"""
