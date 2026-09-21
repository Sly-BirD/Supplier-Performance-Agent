# Supplier Performance Agent

An AI agent that continuously tracks supplier performance across five dimensions — **quality, pricing, delivery/delays, communication, and reliability** — and surfaces that information as scorecards, proactive alerts, and conversational answers.

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy and fill in environment variables
cp .env.example .env

# 3. Run database migrations
alembic upgrade head

# 4. Start the API server
uvicorn src.api.main:app --reload --port 8000

# 5. Start the frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Architecture

- **Agent Orchestrator**: LangGraph state machine with human-in-the-loop approval gates
- **Scoring Engine**: Deterministic, formula-based scoring (0–100 per dimension)
- **Alert Engine**: Rule-based threshold monitoring with email notifications
- **Data Layer**: PostgreSQL + pluggable data adapters (CSV/Excel, with stubs for ERP/Sheets/Email)
- **Config Layer**: Versioned, auditable configuration — every setting is proposed, then user-approved

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Agent | LangGraph, Gemini Flash |
| Database | PostgreSQL, SQLAlchemy 2.0 |
| Validation | Pydantic V2 |
| Frontend | Next.js (React) |
