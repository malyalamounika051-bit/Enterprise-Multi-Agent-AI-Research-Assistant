# Asterline AI Research Assistant — Submission & Verification Links

**Candidate Name:** Mounika Malyala  
**Email:** malyalamounika051@gmail.com  
**Submission Date:** October 28, 2026  
**Assignment:** Batch 5 Take-Home Assignment — A Research Assistant That Remembers

---

## 1. Primary Repository & Codebase
* **GitHub Repository:**  
  [https://github.com/malyalamounika051-bit/Enterprise-Multi-Agent-AI-Research-Assistant](https://github.com/malyalamounika051-bit/Enterprise-Multi-Agent-AI-Research-Assistant)
* **Default Branch:** `main`

---

## 2. Observability & LangSmith Runs

* **LangSmith Project URL:**  
  [https://smith.langchain.com/o/be924490-31a6-44ea-b34a-07669e99f13d/a/asterline-ai-assistant/projects/p/c6f5067a-6366-4b8c-a9d3-be823fbc6de1](https://smith.langchain.com/o/be924490-31a6-44ea-b34a-07669e99f13d/a/asterline-ai-assistant/projects/p/c6f5067a-6366-4b8c-a9d3-be823fbc6de1)
  *(Project Name: `asterline-ai-assistant`)*

* **Public Representative Trace Run Link (No Login Required):**  
  [https://smith.langchain.com/public/ea137c4a-adf2-4bb6-8c8e-2796263cb101/r/0ef58842-7c6c-4245-b4b4-90848b33b0bc?start_time=2026-10-27T13%3A45%3A24.466834Z](https://smith.langchain.com/public/ea137c4a-adf2-4bb6-8c8e-2796263cb101/r/0ef58842-7c6c-4245-b4b4-90848b33b0bc?start_time=2026-10-27T13%3A45%3A24.466834Z)
  * Demonstrates the multi-agent execution pipeline: Memory Agent retrieval → Hybrid Research retrieval → Verification Agent temporal supersession reasoning (`retention:0` 20d superseding `security:1` 60d) → Grounded Synthesis.

* **Offline Fallback Inspector:**  
  For evaluation without network/LangSmith access, every answer in the local web interface features an **"Inspect 3-Agent Workflow Trace"** button that reveals real-time reasoning spans, query inputs, outputs, and latencies from the local SQLite trace store.

---

## 3. Key Deliverables & Documentation Index

All required architectural and evaluation reports are included in the `docs/` folder:
1. `docs/architecture_design.md`: Deep-dive into Agent A, B, and C responsibilities, database schema, Mermaid workflow diagram, and trade-offs.
2. `docs/evaluation_report.md`: Reproducible 15-category evaluation covering grounding, temporal supersession, and user privacy isolation.
3. `docs/ai_disclosure.md`: Transparent AI-use disclosure statement detailing tools, human verification, and code validation protocols.

---

## 4. Single-Command Launch Instructions

* **Windows Command Prompt:**  
  `launch.bat`
* **Windows PowerShell:**  
  `.\launch.ps1`
* **Local Web UI:** `http://localhost:5173`
* **Backend API / Swagger Docs:** `http://127.0.0.1:8000/docs`
