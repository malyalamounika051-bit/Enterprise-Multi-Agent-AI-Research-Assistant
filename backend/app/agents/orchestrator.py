import time
from typing import Dict, Any, List, Optional, TypedDict
from .researcher import ResearchAgent
from .verifier import VerificationAgent
from .memory import MemoryAgent
from .llm import get_llm_client
from ..observability.tracer import TraceRecorder
from ..rag.vector_store import ChunkDocument

class AgentState(TypedDict, total=False):
    user_id: str
    conversation_id: str
    user_message: str
    active_memories: List[Dict[str, Any]]
    explicit_memory_action: Optional[Dict[str, Any]]
    candidate_evidence: List[ChunkDocument]
    verification_report: Dict[str, Any]
    final_answer: str
    citations: List[Dict[str, Any]]
    tracer: TraceRecorder

class MultiAgentOrchestrator:
    """Orchestrates Agent A (Researcher), Agent B (Verifier), and Agent C (Memory)."""
    def __init__(self):
        self.research_agent = ResearchAgent()
        self.verification_agent = VerificationAgent()
        self.memory_agent = MemoryAgent()
        self.llm = get_llm_client()

    def run_flow(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        tracer: Optional[TraceRecorder] = None
    ) -> Dict[str, Any]:
        """Executes the complete multi-agent lifecycle with strict boundaries and full tracing."""
        if tracer is None:
            tracer = TraceRecorder()

        state: AgentState = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_message": user_message,
            "active_memories": [],
            "explicit_memory_action": None,
            "candidate_evidence": [],
            "verification_report": {},
            "final_answer": "",
            "citations": [],
            "tracer": tracer
        }

        # Step 1: Memory Inbound Node (Agent C)
        # Check explicit commands (forget, correct)
        explicit_action = self.memory_agent.detect_and_handle_explicit_actions(
            user_id=user_id,
            user_message=user_message,
            tracer=tracer
        )
        state["explicit_memory_action"] = explicit_action

        # Retrieve user-isolated active memories
        memories = self.memory_agent.retrieve_context(
            user_id=user_id,
            query=user_message,
            tracer=tracer
        )
        state["active_memories"] = memories

        # If user asked explicitly to forget or correct memory, fulfill immediately
        if explicit_action:
            if explicit_action["action"] == "forgotten":
                answer = f"I have forgotten that detail: '{explicit_action['content']}'. It has been removed from your active profile."
            else:
                answer = f"I have updated your memory to: '{explicit_action['new_content']}' (previously: '{explicit_action['old_content']}')."

            state["final_answer"] = answer
            state["citations"] = []
            return {
                "answer": answer,
                "citations": [],
                "agent_trace": tracer.get_trace(),
                "memories_used": [m["content"] for m in memories],
                "explicit_action": explicit_action
            }

        # Step 2: Research Node (Agent A)
        candidate_evidence = self.research_agent.research(
            user_query=user_message,
            user_memories=memories,
            tracer=tracer
        )
        state["candidate_evidence"] = candidate_evidence

        # Step 3: Verification Node (Agent B)
        verification_report = self.verification_agent.analyze_evidence(
            user_query=user_message,
            candidate_chunks=candidate_evidence,
            user_memories=memories,
            tracer=tracer
        )
        state["verification_report"] = verification_report

        # Step 4: Synthesis Node (LLM / Grounded Answer Generator)
        t_synth = time.time()
        
        evidence_dicts = [
            {
                "chunk_id": c.chunk_id,
                "title": c.title,
                "text": c.text,
                "published": c.published,
                "doc_id": c.doc_id
            }
            for c in verification_report.get("verified_chunks", candidate_evidence)
        ]
        
        # Check if user message is primarily a preference or role declaration
        msg_lower = user_message.lower().strip()
        is_pref = any(k in msg_lower for k in ["always format", "i prefer", "always answer", "my preference is"])
        
        if not verification_report.get("sufficient_evidence"):
            raw_answer = (
                f"{verification_report.get('missing_evidence_reason', 'Based on official Asterline documentation, there is no information or recorded policy regarding this topic.')} "
                "The approved knowledge base only covers Asterline workflow-monitoring software, internal runbooks, and policies."
            )
        elif is_pref:
            raw_answer = f"I have noted your preference: '{user_message.strip()}'. I will remember this preference across your sessions."
        else:
            system_prompt = (
                "You are the Asterline AI Research Assistant for Asterline Labs employees.\n"
                "Answer strictly using the provided documentary evidence chunks.\n"
                "Cite every fact using [chunk_id] (e.g. [retention:0]).\n"
                "Honor explicit supersession and policy updates.\n"
                "Never use personal user memories as proof for Asterline company policies."
            )

            raw_answer = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_message,
                evidence_chunks=evidence_dicts,
                supersession_notes=verification_report.get("supersession_notes", []),
                user_memories=memories
            )

        # Validate citations
        final_answer, citations = self.verification_agent.validate_and_format_citations(
            text=raw_answer,
            available_chunks=verification_report.get("verified_chunks", candidate_evidence)
        )
        state["final_answer"] = final_answer
        state["citations"] = citations

        tracer.add_step(
            agent_name="Synthesis & Grounding",
            action="synthesize_response",
            inputs={"query": user_message, "evidence_chunks_count": len(evidence_dicts)},
            outputs={
                "answer_length": len(final_answer),
                "citations_count": len(citations),
                "citations": [c["chunk_id"] for c in citations]
            },
            decision_notes="Synthesized grounded answer with verified documentary citations.",
            duration_ms=round((time.time() - t_synth) * 1000, 2)
        )

        # Step 5: Memory Outbound Node (Agent C)
        # Extract new durable user preferences or context
        new_memories = self.memory_agent.extract_and_store_context(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            tracer=tracer
        )

        return {
            "answer": final_answer,
            "citations": citations,
            "agent_trace": tracer.get_trace(),
            "memories_used": [m["content"] for m in memories],
            "new_memories_extracted": [m["content"] for m in new_memories],
            "supersession_notes": verification_report.get("supersession_notes", []),
            "conflicts_detected": verification_report.get("conflicts_detected", [])
        }

_orchestrator_instance = None
def get_orchestrator() -> MultiAgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MultiAgentOrchestrator()
    return _orchestrator_instance
