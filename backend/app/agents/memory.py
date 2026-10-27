import re
import time
from typing import List, Dict, Any, Optional
from ..db.database import (
    get_memories,
    save_memory,
    correct_memory,
    forget_memory,
    get_memory_audit_logs
)
from ..observability.tracer import TraceRecorder

class MemoryAgent:
    """Agent C: Manages user-specific durable memories, corrections, forgetting, and privacy isolation."""
    def __init__(self):
        self.name = "Memory Agent"

    def retrieve_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        tracer: Optional[TraceRecorder] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve only active memories belonging strictly to user_id."""
        t0 = time.time()
        active_memories = get_memories(user_id=user_id, status="active")
        
        # Keyword / relevance reordering if query is provided
        relevant = []
        if query:
            q_words = set(re.findall(r"\w+", query.lower()))
            for m in active_memories:
                m_words = set(re.findall(r"\w+", m["content"].lower()))
                overlap = len(q_words.intersection(m_words))
                relevant.append((overlap, m))
            relevant.sort(key=lambda x: x[0], reverse=True)
            result = [m for _, m in relevant]
        else:
            result = active_memories

        duration_ms = round((time.time() - t0) * 1000, 2)
        if tracer:
            tracer.add_step(
                agent_name=self.name,
                action="retrieve_user_memories",
                inputs={"user_id": user_id, "query": query},
                outputs={
                    "user_id": user_id,
                    "retrieved_count": len(result),
                    "memory_ids": [m["memory_id"] for m in result],
                    "categories": list(set(m["category"] for m in result))
                },
                decision_notes=f"Retrieved {len(result)} active user-isolated memories for user {user_id}.",
                duration_ms=duration_ms
            )

        return result

    def detect_and_handle_explicit_actions(
        self,
        user_id: str,
        user_message: str,
        tracer: Optional[TraceRecorder] = None
    ) -> Optional[Dict[str, Any]]:
        """Checks if user explicitly commanded the assistant to forget or correct something."""
        msg_lower = user_message.lower().strip()
        
        # 1. Forget command: e.g. "forget that I am on-call", "delete my memory about Dublin"
        if msg_lower.startswith("forget") or "please forget" in msg_lower or "delete my memory" in msg_lower:
            active_mems = get_memories(user_id=user_id, status="active")
            target_topic = re.sub(r"^(please )?(forget|delete my memory)( about| that)?", "", msg_lower).strip()
            
            for m in active_mems:
                if any(w in m["content"].lower() for w in target_topic.split() if len(w) > 3) or target_topic in m["content"].lower():
                    forget_memory(memory_id=m["memory_id"], user_id=user_id)
                    action_result = {
                        "action": "forgotten",
                        "memory_id": m["memory_id"],
                        "content": m["content"],
                        "message": f"Successfully forgot: '{m['content']}'"
                    }
                    if tracer:
                        tracer.add_step(
                            agent_name=self.name,
                            action="forget_memory",
                            inputs={"user_id": user_id, "instruction": user_message},
                            outputs=action_result,
                            decision_notes=f"Soft-deleted memory {m['memory_id']} per user explicit request."
                        )
                    return action_result

        # 2. Correction command: e.g. "actually my project is London, not Dublin", "correct that to..."
        if "actually" in msg_lower or "correction:" in msg_lower or "not " in msg_lower and "but " in msg_lower:
            active_mems = get_memories(user_id=user_id, status="active")
            # If user mentions replacing a previous detail
            for m in active_mems:
                if m["category"] == "project" and ("project" in msg_lower or "working on" in msg_lower):
                    # Extract new project
                    new_val = user_message.strip()
                    correct_memory(memory_id=m["memory_id"], user_id=user_id, new_content=new_val, reason="User corrected project")
                    action_result = {
                        "action": "corrected",
                        "memory_id": m["memory_id"],
                        "old_content": m["content"],
                        "new_content": new_val,
                        "message": f"Updated memory to: '{new_val}'"
                    }
                    if tracer:
                        tracer.add_step(
                            agent_name=self.name,
                            action="correct_memory",
                            inputs={"user_id": user_id, "instruction": user_message},
                            outputs=action_result,
                            decision_notes=f"Updated memory {m['memory_id']} with new user correction."
                        )
                    return action_result

        return None

    def extract_and_store_context(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        tracer: Optional[TraceRecorder] = None
    ) -> List[Dict[str, Any]]:
        """Extract durable user context (preferences, active projects, roles) and persist them."""
        t0 = time.time()
        msg = user_message.strip()
        msg_lower = msg.lower()
        extracted = []

        # Avoid storing one-off questions or query noise
        if msg.endswith("?") and not any(k in msg_lower for k in ["i am", "my name", "my project", "i prefer", "always"]):
            return []

        # Pattern 1: User Preferences (e.g. "I prefer concise bullet points", "Always respond with code")
        pref_match = re.search(r"\b(i prefer|always (format|answer|give|respond)|my preference is)\b\s*(.*)", msg_lower)
        if pref_match:
            content = f"User preference: {pref_match.group(0)}"
            # Check duplicate
            existing = [m["content"] for m in get_memories(user_id=user_id)]
            if content not in existing:
                mem = save_memory(
                    user_id=user_id,
                    category="preference",
                    content=content,
                    provenance=f"{conversation_id}"
                )
                extracted.append(mem)

        # Pattern 2: Project Context (e.g. "I am working on Dublin migration", "My current project is signals ingest")
        proj_match = re.search(r"\b(i am working on|i'm working on|my project is|my team is building)\b\s*([a-zA-Z0-9_\-\s]+)", msg, re.IGNORECASE)
        if proj_match:
            content = f"Current project: {proj_match.group(2).strip()}"
            existing = [m["content"] for m in get_memories(user_id=user_id)]
            if content not in existing:
                mem = save_memory(
                    user_id=user_id,
                    category="project",
                    content=content,
                    provenance=f"{conversation_id}"
                )
                extracted.append(mem)

        # Pattern 3: Operational Role / Region Context (e.g. "I am on-call for eu-prod", "I manage us-prod")
        role_match = re.search(r"\b(i am on-call for|i manage|my focus is)\b\s*([a-zA-Z0-9_\-\s]+)", msg, re.IGNORECASE)
        if role_match:
            content = f"Role focus: {role_match.group(2).strip()}"
            existing = [m["content"] for m in get_memories(user_id=user_id)]
            if content not in existing:
                mem = save_memory(
                    user_id=user_id,
                    category="role_context",
                    content=content,
                    provenance=f"{conversation_id}"
                )
                extracted.append(mem)

        duration_ms = round((time.time() - t0) * 1000, 2)
        if extracted and tracer:
            tracer.add_step(
                agent_name=self.name,
                action="extract_and_store_memory",
                inputs={"user_id": user_id, "conversation_id": conversation_id, "message": user_message},
                outputs={"stored_memories": extracted},
                decision_notes=f"Extracted and saved {len(extracted)} durable memories.",
                duration_ms=duration_ms
            )

        return extracted
