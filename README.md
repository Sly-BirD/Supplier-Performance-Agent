# SIGNAL: An AI-Powered Supplier Performance & Intelligence Agent

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-orange?style=for-the-badge&logo=vercel)](https://supplier-performance-agent.vercel.app/)
[![Next.js 16](https://img.shields.io/badge/Frontend-Next.js%2016-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/AI%20Orchestrator-LangGraph-blue?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Neon Database](https://img.shields.io/badge/Database-Neon%20Postgres-00E599?style=for-the-badge&logo=postgresql)](https://neon.tech/)
[![Clerk Auth](https://img.shields.io/badge/Auth-Clerk%20MFA-6C47FF?style=for-the-badge&logo=clerk)](https://clerk.com/)

An autonomous, multi-tenant AI operations platform that continuously tracks, scores, benchmarks, and triages enterprise supplier performance across five core dimensions: **Quality, Pricing, Delivery/Delays, Communication, and Reliability**. 

Designed for procurement teams, category managers, and supply chain operators to replace manual spreadsheet reviews with a real-time data engine, conversational reasoning copilot, and automated anomaly detection.

**Live Application:** [https://supplier-performance-agent.vercel.app/](https://supplier-performance-agent.vercel.app/)

---

##  Key Capabilities

### 1. 5-Dimensional Performance Engine
Deterministic, auditable scoring algorithms that evaluate supplier telemetry on a normalized 0–100 scale:
* **Delivery (25% default):** On-time fulfillment rates, promised vs. actual lead times, and rolling delay windows.
* **Quality (25% default):** Inspection pass rates, reject quantities, and statistical defect anomaly spikes ($> \mu + k\cdot\sigma$).
* **Pricing & Cost (20% default):** Contract baseline adherence, invoice unit price variance, and inflationary drift.
* **Reliability (15% default):** Fulfillment consistency, order completion rates, and purchase order stability.
* **Communication (15% default):** Average SLA response time, inquiry turnaround, and Corrective Action Request (CAR) resolution speed.

### 2. Network Intelligence Command Center
* **Dominant Intelligence Index:** Real-time weighted aggregate score reflecting full network operational health.
* **Key Operational Telemetry Badges:** Live telemetry pills displaying **On-Time SLA %**, **Network Defect Rate %**, **Contract Price Adherence %**, and **Response Latency**.
* **5-Dimension Vital Signs:** Micro progress bar gauges mapping out network-wide averages across all five pillars.
* **Network Trajectory:** Interactive SVG trendline with dynamic time-range filters (`7D`, `14D`, `30D`, `90D`) and predictive convergence curves.

### 3. Anomaly Log & Operational Exceptions
* **Proactive Threshold Triggers:** Instant detection of critical score drops, SLA breaches, defect surges, or price variance exceeding tolerance boundaries.
* **Severity Triaging:** Color-coded classification (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with metric vs. threshold comparison.
* **Prescriptive Action Recommendations:** AI-generated corrective guidance (e.g., *"Initiate risk review and activate secondary supply chain"*).
* **One-Click Acknowledgment:** Audit tracking with state persistence in Neon PostgreSQL.
* **Outbound Alert Dispatch:** Automated high/critical email dispatch via Resend API.

### 4. Interactive Supplier Directory & Matrix Compare
* **Comprehensive Directory:** Search, multi-tier filters (`Preferred`, `Approved`, `Watch`, `Critical`), category filtering, and sorting.
* **Side-by-Side Supplier Compare:** Select multiple vendor nodes to view direct metric diffs, tier classifications, and category comparisons.
* **Executive PDF & CSV Export:** Download audit-ready supplier evaluation reports with a single click.

### 5. Schema-Agnostic File Ingestion & Connectors
* **Instant Ingestion:** Drag-and-drop any CSV, TSV, or Excel export without reshaping data.
* **Semantic Schema Inference:** Classifies date pairs, defect columns, pricing data, and identifiers automatically.
* **Live Cloud Connectors Roadmap:** Integrated connector suite for continuous 15-minute polling from Google Sheets, SAP S/4HANA, NetSuite, and Coupa.

### 6. Conversational Copilot (SIGNAL AI)
* Built on **LangGraph** state machines and **Google Gemini Flash**.
* Instant natural language Q&A (e.g., *"Which suppliers in North America are deteriorating?"*, *"Compare AeroFlow vs Nordic Circuitry"*).
* **Human-in-the-Loop Governance:** Proposed configuration changes (weights, alert rules) require explicit user approval before execution.
* Accessible anytime via global keyboard shortcut (`⌘K` / `Ctrl+K`).

### 7. Multi-Tenant Isolation & Security
* **Tenant Scoping:** Every supplier, transaction record, scorecard, and alert is strictly isolated by `user_id`.
* **Zero Cross-Tenant Leakage:** Enforced at the SQLAlchemy ORM layer and verified with cryptographic JWT tokens.
* **Authentication:** Enterprise-ready authentication powered by **Clerk** (Email, Google, GitHub SSO).

---

##  System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Frontend (Next.js 16 / Vercel)                    │
│   Overview Dashboard │ Exceptions Feed │ Compare Matrix │ Signal Chat   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │  Clerk JWT Bearer Token / REST
┌────────────────────────────────────▼────────────────────────────────────┐
│                    Backend API & Engine (FastAPI / Uvicorn)             │
│  ┌───────────────────────┐  ┌───────────────────┐  ┌──────────────────┐ │
│  │    LangGraph Agent    │  │   Scoring Engine  │  │   Alert Engine   │ │
│  │ (Gemini Intent Router)│  │ (5-Dim Algorithms)│  │ (Rule Detection) │ │
│  └───────────────────────┘  └───────────────────┘  └──────────────────┘ │
│  ┌───────────────────────┐  ┌───────────────────┐  ┌──────────────────┐ │
│  │    Schema Inference   │  │   Config Store    │  │  Resend Email    │ │
│  │ (Semantic Col Mapper) │  │  (Audited Rules)  │  │  (Alert Dispatch)│ │
│  └───────────────────────┘  └───────────────────┘  └──────────────────┘ │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │  AsyncPG / SQLAlchemy 2.0 (SSL)
┌────────────────────────────────────▼────────────────────────────────────┐
│                  Neon Serverless PostgreSQL Database                    │
│      Suppliers · Transactions · ScoreSnapshots · Alerts · Configs       │
│                  (Strict Multi-Tenant Row-Level Scoping)                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

##  Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | Next.js 16 (App Router), React 19 | Turbopack, Tailwind CSS, Radix UI, Lucide Icons |
| **Backend** | Python 3.11+, FastAPI | Uvicorn, Pydantic V2, Asyncio |
| **Agent Orchestration** | LangGraph, LangChain | State Machine Graph with Human-in-the-Loop Gates |
| **LLM Provider** | Google Gemini 2.0 / Flash | Structured output, intent routing, analytical summaries |
| **Database** | Neon Serverless PostgreSQL | SQLAlchemy 2.0 asyncpg, connection pooling, SSL |
| **Authentication** | Clerk Auth | Multi-Factor Authentication, JWT verification, session management |
| **Email Service** | Resend API | Asynchronous HTML alert dispatch for critical exceptions |
| **Deployment** | Vercel (Frontend), Render/Docker (Backend) | Containerized deployment with dynamic backend rewrites |

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
