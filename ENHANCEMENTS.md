# Enhancements & Roadmap

This document lists planned upgrades beyond the hackathon MVP, split into
**advanced/technical functions** and **user-friendly features**. Some are
already stubbed out in `app/future/` (clearly separated from the working
core so judges know exactly what's live vs. planned). Others are design
notes only.

Status legend: 🟢 stubbed & runnable · 🟡 designed, not implemented · ⚪ idea

---

## Advanced / technical functions

| Feature | Status | File | Notes |
|---|---|---|---|
| Parallel task execution | 🟢 | `app/future/parallel_orchestrator.py` | Runs independent tasks (`search`, `enrich`) concurrently with `asyncio.gather` instead of sequentially. Drop-in replacement for `ResearchOrchestrator.run()`. |
| Real x402 payment provider | 🟢 | `app/future/real_payment_provider.py` | Implements the same `PaymentProvider` interface as `MockPaymentProvider`. Currently raises `NotImplementedError` at the network call — swap in a real facilitator SDK (wallet signing + settlement) to go live. |
| Streaming responses (SSE) | 🟢 | `app/future/streaming.py` | Server-Sent Events endpoint that pushes each report section to the client as it completes, instead of waiting for the full report. |
| Result caching | 🟢 | `app/future/caching.py` | In-memory TTL cache keyed on normalized query text, to avoid re-paying/re-running identical research queries within a session. |
| API auth + rate limiting | 🟢 | `app/future/rate_limiter.py` | Per-API-key sliding-window rate limiter, so the agent's spend policy can't be bypassed by hammering the endpoint. |
| Multi-provider tool fallback | 🟡 | — | If a real search/fact-check API fails or times out, fall back to a secondary provider before falling back to mock data. |
| Vector-store memory | ⚪ | — | Persist past research reports in a vector DB so future queries can reuse prior findings instead of re-searching. |

## User-friendly features

| Feature | Status | File | Notes |
|---|---|---|---|
| Export report (Markdown / plain text) | 🟢 | `app/future/export.py` | Wired into `main.py` as `GET /research/export/{format}` — works today, no extra setup. |
| Query history | 🟢 | `app/future/history.py` | In-memory session history, wired into `main.py` as `GET /history`. Swap the in-memory list for a DB for persistence across restarts. |
| Live progress indicator in UI | 🟡 | — | Pairs with the SSE streaming endpoint above — show a step-by-step progress bar as each task (search → enrich → fact-check → summarize) completes. |
| Budget slider in UI | 🟡 | — | Let users drag a slider to set `max_per_call` / `max_per_session` instead of only via the API body, with a live preview of what would get rejected. |
| Shareable report links | ⚪ | — | Persist a completed report under a short ID (`/report/{id}`) so a research result can be shared without re-running the query. |
| Dark mode | ⚪ | — | Cosmetic, but frequently requested — toggle in `index.html`. |

---

## Suggested implementation order

1. **Parallel execution** — biggest speed win, low risk, no new dependencies.
2. **Export + history** — already wired, just needs a UI button to surface them.
3. **Streaming (SSE) + progress bar** — best demo/UX payoff together.
4. **Real x402 provider** — the "make it actually production-real" milestone once a facilitator SDK/API key is available.
5. **Caching + rate limiting** — hardening once the above is stable.

---

## Contributing

Everything in `app/future/` follows the same interface contracts as the
core app (`PaymentProvider`, `ToolResult`, etc.) so it can be swapped in
without touching `orchestrator.py`'s public API. See inline docstrings in
each file for exact wiring instructions.
