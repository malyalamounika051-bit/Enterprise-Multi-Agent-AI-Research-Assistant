import re
import time
from typing import List, Dict, Any, Optional
from ..rag.vector_store import get_vector_store, ChunkDocument
from ..observability.tracer import TraceRecorder

class ResearchAgent:
    """Agent A: Formulates search queries, queries ChromaDB and inverted index, gathers documentary evidence."""
    def __init__(self):
        self.name = "Research Agent"

    def _generate_search_queries(self, user_query: str) -> List[str]:
        queries = [user_query.strip()]
        
        # Specific query expansions for known Asterline systems & incidents
        q_lower = user_query.lower()
        
        if "cold" in q_lower or "retention" in q_lower:
            queries.append("cold storage recovery retention days archive")
            queries.append("retention policy security")
        elif "stipend" in q_lower or "on-call" in q_lower or "oncall" in q_lower:
            queries.append("on-call stipend weekly compensation handbook")
            queries.append("runbook oncall engineer compensation")
        elif "deduplication" in q_lower or "export" in q_lower or "inc-2025-12" in q_lower:
            queries.append("export job deduplication INC-2025-12 record_hash")
            queries.append("warehouse export position based deduplication patch 2.1.2")
        elif "timeout" in q_lower or "aql" in q_lower or "signals" in q_lower:
            queries.append("Signals AQL query timeout 50 seconds 25 seconds")
            queries.append("release-23 AQL timeout upgrade")
        elif "office" in q_lower or "location" in q_lower or "pune" in q_lower or "dublin" in q_lower:
            queries.append("company overview office Pune Dublin locations")

        # Entity extraction for incident codes or version tags
        incidents = re.findall(r"inc-\d{4}-\d+", q_lower)
        for inc in incidents:
            queries.append(f"incident report {inc.upper()}")

        return list(dict.fromkeys(queries))  # preserve order & unique

    def research(
        self,
        user_query: str,
        user_memories: Optional[List[Dict[str, Any]]] = None,
        tracer: Optional[TraceRecorder] = None
    ) -> List[ChunkDocument]:
        t0 = time.time()
        vector_store = get_vector_store()
        
        queries = self._generate_search_queries(user_query)
        evidence_map: Dict[str, ChunkDocument] = {}

        for q in queries:
            hits = vector_store.hybrid_search(q, top_k=5)
            for h in hits:
                if h.chunk_id not in evidence_map or (h.score and h.score > (evidence_map[h.chunk_id].score or 0)):
                    evidence_map[h.chunk_id] = h

        evidence = sorted(evidence_map.values(), key=lambda x: (x.score or 0.0), reverse=True)[:8]

        duration_ms = round((time.time() - t0) * 1000, 2)
        if tracer:
            tracer.add_step(
                agent_name=self.name,
                action="retrieve_evidence",
                inputs={"query": user_query, "expanded_queries": queries},
                outputs={
                    "evidence_count": len(evidence),
                    "chunk_ids": [e.chunk_id for e in evidence],
                    "titles": [e.title for e in evidence]
                },
                decision_notes=f"Retrieved {len(evidence)} candidate chunks using hybrid vector & keyword matching.",
                duration_ms=duration_ms
            )

        return evidence
