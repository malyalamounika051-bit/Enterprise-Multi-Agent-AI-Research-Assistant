import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from ..config import settings
from ..db.database import (
    get_users,
    get_user,
    create_conversation,
    get_conversations,
    get_conversation,
    add_message,
    get_messages,
    get_memories,
    save_memory,
    correct_memory,
    forget_memory,
    get_memory_audit_logs,
    get_latest_eval_run
)
from ..agents.orchestrator import get_orchestrator
from ..rag.vector_store import get_vector_store
from ..observability.tracer import is_langsmith_enabled

router = APIRouter()

# Models
class ChatRequest(BaseModel):
    user_id: str
    conversation_id: Optional[str] = None
    message: str

class MemoryCreateRequest(BaseModel):
    user_id: str
    category: str
    content: str
    provenance: Optional[str] = "Manual entry"

class MemoryUpdateRequest(BaseModel):
    user_id: str
    content: str
    reason: Optional[str] = "User correction"

# System Status
@router.get("/system/status")
def get_system_status():
    vs = get_vector_store()
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "corpus_chunks_indexed": vs.collection.count(),
        "langsmith_connected": is_langsmith_enabled(),
        "langsmith_project": settings.LANGCHAIN_PROJECT,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL
    }

# User Endpoints
@router.get("/users")
def list_users():
    return get_users()

@router.get("/users/{user_id}")
def get_user_profile(user_id: str):
    u = get_user(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

# Conversation Endpoints
@router.get("/conversations")
def list_conversations(user_id: str = Query(...)):
    return get_conversations(user_id)

@router.post("/conversations")
def new_conversation(payload: Dict[str, Any] = Body(...)):
    user_id = payload.get("user_id")
    title = payload.get("title", "New Research Session")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return create_conversation(user_id=user_id, title=title)

@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str):
    return get_messages(conversation_id)

# Main Multi-Agent Chat Endpoint
@router.post("/chat")
def chat(req: ChatRequest):
    user_id = req.user_id
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cid = req.conversation_id
    if not cid:
        c = create_conversation(user_id=user_id, title=req.message[:40] + "...")
        cid = c["conversation_id"]

    # 1. Store user message in SQLite
    add_message(
        conversation_id=cid,
        sender="user",
        content=req.message
    )

    # 2. Run multi-agent orchestrator
    orchestrator = get_orchestrator()
    result = orchestrator.run_flow(
        user_id=user_id,
        conversation_id=cid,
        user_message=req.message
    )

    # 3. Store assistant message with citations and full agent trace
    msg = add_message(
        conversation_id=cid,
        sender="assistant",
        content=result["answer"],
        citations=result.get("citations", []),
        agent_trace=result.get("agent_trace", [])
    )

    return {
        "conversation_id": cid,
        "message_id": msg["message_id"],
        "answer": result["answer"],
        "citations": result.get("citations", []),
        "agent_trace": result.get("agent_trace", []),
        "memories_used": result.get("memories_used", []),
        "new_memories_extracted": result.get("new_memories_extracted", []),
        "supersession_notes": result.get("supersession_notes", []),
        "conflicts_detected": result.get("conflicts_detected", [])
    }

# User-Isolated Memory Management Endpoints
@router.get("/memories")
def list_memories(user_id: str = Query(...), status: str = Query("active")):
    return get_memories(user_id=user_id, status=status)

@router.post("/memories")
def add_user_memory(payload: MemoryCreateRequest):
    return save_memory(
        user_id=payload.user_id,
        category=payload.category,
        content=payload.content,
        provenance=payload.provenance or "Manual UI entry"
    )

@router.put("/memories/{memory_id}")
def update_user_memory(memory_id: str, payload: MemoryUpdateRequest):
    success = correct_memory(
        memory_id=memory_id,
        user_id=payload.user_id,
        new_content=payload.content,
        reason=payload.reason or "Manual correction via UI"
    )
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or does not belong to user")
    return {"status": "success", "memory_id": memory_id}

@router.delete("/memories/{memory_id}")
def delete_user_memory(memory_id: str, user_id: str = Query(...), hard_delete: bool = Query(False)):
    success = forget_memory(
        memory_id=memory_id,
        user_id=user_id,
        hard_delete=hard_delete
    )
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or does not belong to user")
    return {"status": "success", "action": "hard_delete" if hard_delete else "soft_delete"}

@router.get("/memories/audit")
def memory_audit(user_id: str = Query(...)):
    return get_memory_audit_logs(user_id=user_id)

from ..evaluation.evaluator import ReproducibleEvaluator

# Evaluation Endpoints
@router.post("/evaluation/run")
def trigger_eval():
    evaluator = ReproducibleEvaluator()
    return evaluator.run_all_evaluations()

@router.get("/evaluation/latest")
def get_eval():
    latest = get_latest_eval_run()
    if not latest:
        return {"status": "no_runs", "message": "No evaluation runs recorded yet. Trigger one via POST /api/evaluation/run"}
    return latest
