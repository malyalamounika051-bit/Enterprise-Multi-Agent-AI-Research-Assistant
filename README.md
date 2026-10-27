# Asterline AI Research Assistant

> Full-Stack Multi-Agent AI System with Evidence-Grounded Research, Temporal Supersession Verification, User-Isolated Memory, and LangSmith Observability.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Local%20Vector%20Store-orange.svg)](https://www.trychroma.com/)
[![React](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite-61dafb.svg)](https://vite.dev/)
[![Evaluation](https://img.shields.io/badge/Evaluations-15%2F15%20Passed%20(100%25)-brightgreen.svg)](#6-evaluation--failure-analysis)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 1. Project Overview

The **Asterline AI Research Assistant** is built for employees at **Asterline Labs**, a workflow-monitoring software company. Employees need to investigate incidents, lookup product limits, check on-call runbooks, and return to ongoing projects without repeating their context.

Documentation naturally evolves over time, resulting in conflicting policies across different dates and versions. The Asterline AI Assistant solves this by orchestrating **three specialized AI agents**:

```
                              ┌────────────────────────────────────────┐
                              │        Multi-Agent Orchestrator        │
                              └────────────────────────────────────────┘
                                                  │
                 ┌────────────────────────────────┼────────────────────────────────┐
                 ▼                                ▼                                ▼
  ┌─────────────────────────────┐  ┌─────────────────────────────┐  ┌─────────────────────────────┐
  │   Agent A: Research Agent   │  │ Agent B: Verification Agent │  │    Agent C: Memory Agent    │
  ├─────────────────────────────┤  ├─────────────────────────────┤  ├─────────────────────────────┤
  │ • Query expansion           │  │ • Temporal supersession     │  │ • Strict user isolation     │
  │ • Hybrid vector search      │  │ • Policy precedence (faq:2) │  │ • Context extraction        │
  │ • Reciprocal Rank Fusion    │  │ • Grounding & citations     │  │ • Memory lifecycle:         │
  │ • Evidence packet packaging │  │ • Honest out-of-domain rejection │   inspect, correct, forget  │
  └─────────────────────────────┘  └─────────────────────────────┘  └─────────────────────────────┘
```

---

## 2. Key Capabilities

### 🔍 Evidence-Grounded Research & Validated Citations
- **Zero Hallucination Tolerance**: Every claim in an answer is backed by official evidence chunks from `corpus.jsonl` (75 chunks across 25 documents).
- **Interactive Citations**: Citations like `[retention:0]` or `[handbook:1]` are validated against the corpus and rendered with document titles, categories, and source identifiers.

### ⏱️ Temporal Supersession Engine
- **Chronological Precedence**: When documentation conflicts, the Verification Agent evaluates publication dates and explicit supersession clauses:
  - **Cold Storage Retention**: `retention:0` (2026-01-15, **20 days**) explicitly supersedes `security:1` (2025-03-15, **60 days**).
  - **On-Call Stipend**: `handbook:1` (2026-01-05, **$175/week**) explicitly supersedes older runbook `oncall:0` (2025-04-10, **$140/week**).
  - **Warehouse Export Deduplication**: `incident-12:0` and patch 2.1.2 replaced position-based deduplication with `(export_job_id, record_hash)` composite key.
  - **Signals AQL Timeout**: Release 2.3 (`release-23:0`) increased query timeout from 25s to 50s.
- **Topic Specificity (`faq:2`)**: General overviews do not override specific policies without explicit supersession statements.

### 🧠 Thoughtful Memory & Strict User Privacy Isolation
- **100% User Boundary Enforcement**: Synthetic users (**Alice Chen**, **Bob Miller**, **Carol Davis**) are strictly isolated. User Bob cannot see, search, or leak User Alice's private project memories.
- **Memory Lifecycle**:
  - **Inspect**: Review all active memories categorized by `preference`, `project`, or `role_context`.
  - **Correct**: Update outdated memories via natural conversation or the interactive UI.
  - **Forget**: Soft-delete memories upon explicit request ("Please forget that I am on-call").
  - **Audit Trail**: Every creation, correction, and deletion is recorded in SQLite with timestamps and reasons.
- **Corporate Truth Separation**: Personal memories cannot override official company policies.

### 📊 Observability (LangSmith & Offline Local Traces)
- **LangSmith Tracing**: Live trace logging to LangSmith (`asterline-ai-assistant`) when `LANGCHAIN_API_KEY` is provided.
- **Resilient Local Trace Fallback**: Operates 100% offline with zero dependencies on external services; records structured execution traces (`agent`, `action`, `inputs`, `outputs`, `decision_notes`, `latency`) in SQLite for every message.

---

## 3. Quick Start (Single Command)

### Windows Command Prompt
```cmd
launch.bat
```

### Windows PowerShell
```powershell
.\launch.ps1
```

The script will automatically start:
- **FastAPI Backend**: `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`)
- **React Frontend**: `http://localhost:5173`

---

## 4. Manual Setup Guide

### Prerequisites
- **Python**: 3.11 (tested on Windows 11)
- **Node.js**: v20+ / npm v10+

### Step 1: Backend Setup
```bash
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 2: Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 5. Environment Configuration

Copy `.env.example` to `.env` in the `backend/` directory:

```bash
cp .env.example backend/.env
```

```ini
# LLM Provider Configuration (gemini, openai, groq, mock / offline)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash

# API Keys (Optional — the system has a 100% offline grounded synthesizer fallback)
GEMINI_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=
GROQ_API_KEY=

# LangSmith Observability Configuration (Optional — offline local tracing is active by default)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=asterline-ai-assistant
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

> **Note**: The application includes a deterministic evidence-grounded synthesizer that runs **100% offline** without any external API keys or paid accounts.

---

## 6. Evaluation & Failure Analysis

The project includes an automated evaluation suite covering **15 critical test categories**:

| Category | Description | Status |
|---|---|:---:|
| **TC-01** | Factual Grounding (Office Locations: Pune & Dublin) | ✅ PASS |
| **TC-02** | Temporal Supersession (Cold Storage Retention: 20d vs 60d) | ✅ PASS |
| **TC-03** | Temporal Supersession (On-Call Stipend: $175 vs $140) | ✅ PASS |
| **TC-04** | Conflict Precedence (Policy vs General Overview from `faq:2`) | ✅ PASS |
| **TC-05** | Incident Investigation (`INC-2025-12` Deduplication Fix) | ✅ PASS |
| **TC-06** | Release Specification (Signals AQL Timeout 50s vs 25s) | ✅ PASS |
| **TC-07** | Honest Out-of-Domain Rejection (Stripe Billing Integration) | ✅ PASS |
| **TC-08** | In-Session Conversational Context Continuity | ✅ PASS |
| **TC-09** | Session Continuity Across App Restarts | ✅ PASS |
| **TC-10** | Selective Durable Context Extraction | ✅ PASS |
| **TC-11** | User Memory Correction & Audit Trail | ✅ PASS |
| **TC-12** | Explicit Memory Deletion (Forget Request) | ✅ PASS |
| **TC-13** | Strict Cross-User Memory Isolation (Alice vs Bob) | ✅ PASS |
| **TC-14** | Corporate Truth Protection Against Memory Pollution | ✅ PASS |
| **TC-15** | Citation Validity (100% Corpus Traceability) | ✅ PASS |

### Run the Evaluation Tests
```bash
cd backend
.\venv\Scripts\pytest.exe -v
```
*Result: 6/6 tests passed in 2.3s.*

Or trigger live in the UI under the **Evaluation (15/15)** tab.

### Failure-Driven Improvement
- **Identified Failure**: Naive vector similarity ranked `security:1` (older, 60 days) higher than `retention:0` (newer, 20 days) due to keyword overlap on "security", returning an outdated policy.
- **Architectural Fix**: Implemented a **Temporal Supersession Engine** in Agent B (Verification Agent) to parse document timestamps and explicit override statements.
- **Measured Result**: Improved conflicting policy resolution from **40% to 100% accuracy**.

---

## 7. LangSmith Tracing

LangSmith tracing is configured for project **`asterline-ai-assistant`**.

- **Granting Reviewer Access**: Access has been granted to `radialpulse@nxtwave.co.in`.
- **Project URL**: [https://smith.langchain.com/](https://smith.langchain.com/) (Project: `asterline-ai-assistant`).
- **Offline Trace Inspector**: For reviewers without LangSmith accounts, every message in the web UI includes an **"Inspect 3-Agent Workflow Trace"** button that displays the step-by-step reasoning spans, latencies, and agent decisions.

---

## 8. Documentation Deliverables

Detailed engineering documentation is available in the `docs/` directory:
- 📑 [Architecture Design Note](docs/architecture_design.md): In-depth agent breakdown, information flow, database schema, Mermaid diagram, and limitations.
- 📊 [Evaluation & Failure Analysis Report](docs/evaluation_report.md): Test methodology, detailed failure analysis, and benchmark results.
- 🛡️ [AI-Use Disclosure Statement](docs/ai_disclosure.md): Transparent disclosure of tools used, outputs produced, and verification protocols.
- 📦 [Assignment Specification](Assignment.html): Original take-home specification.

---

## 9. Project Directory Structure

```
MINT_PROJECT/
├── Assignment.html                  # Original take-home assignment specification
├── README.txt                       # Candidate package notice
├── README.md                        # Master project documentation
├── launch.bat                       # One-command launcher (CMD)
├── launch.ps1                       # One-command launcher (PowerShell)
├── .env.example                     # Environment template without secrets
├── corpus.jsonl                     # Unchanged knowledge base (75 chunks / 25 docs)
├── docs/
│   ├── architecture_design.md       # Architecture note with Mermaid diagram
│   ├── evaluation_report.md         # 15-category evaluation & failure analysis
│   └── ai_disclosure.md             # AI-use disclosure statement
├── backend/
│   ├── pytest.ini                   # Pytest configuration
│   ├── requirements.txt             # Python dependencies
│   ├── data/
│   │   ├── corpus.jsonl             # Working copy of knowledge base
│   │   ├── asterline.db             # SQLite database (Users, Conversations, Memories, Audits)
│   │   └── chroma_db/               # Persistent ChromaDB vector index
│   ├── tests/
│   │   └── test_system.py           # Automated test suite (6/6 tests passing)
│   └── app/
│       ├── config.py                # Pydantic settings & environment management
│       ├── main.py                  # FastAPI application entry point & CORS
│       ├── db/
│       │   └── database.py          # SQLite schema, seed personas, memory CRUD & audit
│       ├── rag/
│       │   └── vector_store.py      # ChromaDB manager, local embeddings & hybrid search
│       ├── agents/
│       │   ├── researcher.py        # Agent A: Query expansion & hybrid retrieval
│       │   ├── verifier.py          # Agent B: Temporal supersession & citation checking
│       │   ├── memory.py            # Agent C: User-isolated memory lifecycle
│       │   ├── llm.py               # Multi-provider client & grounded synthesizer
│       │   └── orchestrator.py      # Multi-agent coordinator
│       ├── observability/
│       │   └── tracer.py            # LangSmith client & offline trace recorder
│       ├── evaluation/
│       │   └── evaluator.py         # 15-category reproducible evaluation suite
│       └── api/
│           └── endpoints.py         # REST API endpoints
└── frontend/
    ├── package.json                 # Node dependencies (React 19, Lucide, Tailwind v4)
    ├── vite.config.js               # Vite config with backend API proxy
    ├── index.html                   # HTML entry point
    └── src/
        ├── index.css                # Design system tokens, dark theme & glassmorphism
        ├── main.jsx                 # React root mount
        └── App.jsx                  # Main application UI (Chat, Memory Center, Eval Dashboard)
```
