# Multi-Step Research Agent

An AI-powered research agent that automatically breaks complex queries into multiple steps — **search, data enrichment, fact-checking, and summarization** — then orchestrates those steps and combines the results into a structured research report with sources.

Built with a policy-guarded **agent payment layer** (x402-style): every tool call is settled against a spend policy before it runs, so the agent can never exceed a set budget mid-research.

**Tech Stack:** Python · FastAPI · Pydantic · REST APIs · Agent Orchestration

---

## What it does

1. A user submits a research query
2. The **planner** decomposes it into an ordered set of tasks (search → enrich → fact-check → summarize)
3. Before each task runs, the **payment guard** checks it against a spend policy (per-call cap, session budget, merchant allowlist) and settles payment
4. If a task is approved, its **tool** runs and returns results with sources and a confidence score
5. The **orchestrator** compiles every section into one structured report, with a full payment ledger attached

If the budget runs out mid-research, later tasks are correctly **rejected** rather than silently skipped — the report shows exactly what ran, what didn't, and why.

---

## 📁 Project Structure

```
multi-step-research-agent/
├── app/
│   ├── main.py                  # FastAPI app: routes, request/response models
│   ├── orchestrator.py          # Coordinates planner → payment → tools → report
│   ├── agents/
│   │   ├── planner.py           # Breaks a query into an ordered task list
│   │   └── tools.py             # search / enrich / fact_check / summarize tools
│   ├── x402/
│   │   └── payment.py           # SpendPolicy, PaymentProvider, MockPaymentProvider
│   ├── future/                  # Advanced enhancements — see ENHANCEMENTS.md
│   │   ├── parallel_orchestrator.py   # Async/concurrent task execution
│   │   ├── real_payment_provider.py   # Scaffold for a live x402 facilitator
│   │   ├── export.py            # Report export (Markdown / plain text) — LIVE
│   │   ├── history.py           # Session query history — LIVE
│   │   ├── streaming.py         # SSE streaming design (planned)
│   │   └── rate_limiter.py      # Per-key rate limiting (planned)
│   └── static/
│       └── index.html           # Minimal frontend to run & visualize a query
├── ENHANCEMENTS.md               # Roadmap: advanced functions + user-friendly features
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/Nishant-Dev301/multi-step-research-agent.git
cd multi-step-research-agent

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn app.main:app --reload
```

Then open:
- **UI:** http://127.0.0.1:8000
- **Interactive API docs:** http://127.0.0.1:8000/docs

No API keys or external accounts are required to run this demo — see [What's real vs. mocked](#-whats-real-vs-mocked-read-this-before-judging) below.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend UI |
| `GET` | `/health` | Health check |
| `POST` | `/research` | Runs a query through the full agent pipeline, returns a structured report |
| `GET` | `/research/export/{fmt}?query=...` | Downloads the most recent report for a query as `markdown` or `txt` |
| `GET` | `/history` | Returns recent queries run in this server session |

Example request:
```json
POST /research
{
  "query": "Impact of autonomous AI agent payments on API economies",
  "max_per_call": 0.05,
  "max_per_session": 0.20
}
```

---

## ✅ What's real vs. mocked (read this before judging)

Being upfront about scope, since this was built under a hackathon deadline:

- **Orchestration logic, task decomposition, and the payment policy guard are fully real and functional** — not mocked. You can set a tight session budget and watch the pipeline correctly halt and mark later tasks as `rejected`.
- **The x402 payment settlement is simulated** (`MockPaymentProvider`). It implements the same shape as a real x402 flow (challenge → sign → settle → ledger) but doesn't call a live facilitator or wallet. A scaffold for a real implementation is in `app/future/real_payment_provider.py`.
- **Search / enrich / fact-check / summarize tools return deterministic mock data** rather than calling live paid APIs, so the demo runs without API keys or network access.

See [`ENHANCEMENTS.md`](./ENHANCEMENTS.md) for the full roadmap of what's planned next, including a working async parallel-execution mode, report export, and query history that are already implemented in `app/future/`.

---

## 🎯 Why this project

Agentic systems that autonomously call paid APIs need a way to guarantee they can't overspend. This project demonstrates that guarantee as a first-class part of the architecture — not bolted on — by settling payment against a policy *before* any tool executes, and stopping cleanly the moment a budget is hit.

---

## 📄 License

Built for [Brainwave Hackathon 2026].
