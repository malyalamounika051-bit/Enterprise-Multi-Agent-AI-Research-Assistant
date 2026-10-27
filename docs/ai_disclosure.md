# AI-Use Disclosure Statement

In accordance with Section 5 of the assignment requirements ("A brief AI-use disclosure"), this document outlines the artificial intelligence tools utilized during the development of the **Asterline AI Research Assistant**, what they helped produce, and the rigorous verification procedures applied to their outputs.

---

## 1. Tools Utilized

- **Antigravity AI Assistant (Gemini 3.8 Flash / Gemini 2.5 Pro)**: Utilized as a pair-programming coding assistant and technical mentor within the Antigravity IDE environment.

---

## 2. What the Tools Helped Produce

1. **Scaffolding and Boilerplate Code**:
   - Initial FastAPI project structure and endpoint routing templates.
   - Pydantic models for request/response serialization.
   - React + Tailwind CSS UI layout structure and Lucide icon integrations.
2. **Dataset Extraction & Validation Scripts**:
   - Python script utilizing `pypdf` to inspect the embedded attachments within the assignment PDF and extract `corpus.jsonl` byte-for-byte.
   - JSON validation script verifying the presence of all 75 chunks across 25 documents with zero missing fields.
3. **Drafting Test Case Fixtures**:
   - Helping draft preliminary assertions and test query variants for the 15 evaluation categories based on the extracted corpus.

---

## 3. Human Verification & Output Validation Methodology

To ensure correctness, reproducibility, and system reliability, all AI-generated code and design elements were subjected to the following verification protocols:

1. **Corpus Integrity Verification**:
   - Verified that `corpus.jsonl` was extracted directly from the PDF embedded attachments without alteration (exactly 36,019 bytes, 75 chunks, 25 documents).
   - Validated that neither chunk text nor metadata values were modified.
2. **Independent Test Execution**:
   - Executed the test suite directly via `pytest` in PowerShell to ensure that tests run natively on the Windows operating system and produce deterministic, reproducible results (6/6 pytest tests passed, 15/15 evaluation categories passed).
3. **Mathematical & Deterministic RAG Verification**:
   - Independently verified the dense cosine projection embedding function (`LocalDenseEmbeddingFunction`) using unit tests in Python, confirming that semantic queries (e.g. cold storage retention) produce strong positive cosine similarity (0.676) while orthogonal topics (e.g. office locations) produce zero similarity (0.0).
4. **Temporal Policy Checking**:
   - Manually audited every temporal supersession rule against the raw text of `retention:0`, `security:1`, `handbook:1`, `oncall:0`, and `incident-12:0` to guarantee that effective dates and explicit override statements are accurately respected.
5. **Security & Privacy Auditing**:
   - Inspected all database queries to ensure that `user_id` filtering is strictly enforced on all memory retrieval and modification operations, verifying that no private context leaks between synthetic user personas.
   - Confirmed that zero API keys or secrets are stored in code or repository commits.
