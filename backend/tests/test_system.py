import pytest
from app.evaluation.evaluator import ReproducibleEvaluator
from app.rag.vector_store import get_vector_store
from app.db.database import get_users, get_memories, save_memory, correct_memory, forget_memory
from app.agents.orchestrator import get_orchestrator

def test_corpus_loaded():
    vs = get_vector_store()
    count = vs.collection.count()
    assert count == 75, f"Expected 75 chunks in ChromaDB, found {count}"

def test_synthetic_users():
    users = get_users()
    user_ids = [u["user_id"] for u in users]
    assert "user_alice" in user_ids
    assert "user_bob" in user_ids
    assert "user_carol" in user_ids

def test_temporal_supersession_cold_storage():
    orchestrator = get_orchestrator()
    res = orchestrator.run_flow(
        user_id="user_alice",
        conversation_id="conv_test_retention",
        user_message="What is the retention period for cold storage recovery?"
    )
    answer = res["answer"]
    assert "20 days" in answer
    assert "retention:0" in [c["chunk_id"] for c in res["citations"]] or "retention:0" in answer

def test_temporal_supersession_oncall_stipend():
    orchestrator = get_orchestrator()
    res = orchestrator.run_flow(
        user_id="user_bob",
        conversation_id="conv_test_stipend",
        user_message="What is the weekly compensation stipend for on-call engineers?"
    )
    answer = res["answer"]
    assert "$175" in answer
    assert "handbook:1" in [c["chunk_id"] for c in res["citations"]] or "handbook:1" in answer

def test_cross_user_memory_isolation():
    save_memory("user_alice", "project", "Confidential Alice Project 999", "pytest")
    bob_memories = get_memories("user_bob")
    assert not any("Project 999" in m["content"] for m in bob_memories), "Isolation breach: Alice's memory in Bob's list!"

def test_reproducible_evaluation_suite():
    evaluator = ReproducibleEvaluator()
    res = evaluator.run_all_evaluations()
    metrics = res["metrics"]
    assert metrics["pass_rate_pct"] == 100.0, f"Expected 100% pass rate, got {metrics['pass_rate_pct']}%"
