import os
import time
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from ..config import settings

# LangSmith Client & configuration
_langsmith_client = None
_langsmith_enabled = False

def init_observability():
    global _langsmith_client, _langsmith_enabled
    if settings.LANGCHAIN_API_KEY and settings.LANGCHAIN_API_KEY.strip():
        try:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT or "asterline-ai-assistant"
            os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
            
            from langsmith import Client
            _langsmith_client = Client()
            _langsmith_enabled = True
            print(f"[Observability] LangSmith enabled for project '{settings.LANGCHAIN_PROJECT}'")
        except Exception as e:
            print(f"[Observability] Failed to initialize LangSmith ({e}). Running in offline trace mode.")
            _langsmith_enabled = False
    else:
        print("[Observability] No LANGCHAIN_API_KEY set. Running in resilient local offline trace mode.")
        _langsmith_enabled = False

def is_langsmith_enabled() -> bool:
    return _langsmith_enabled

class TraceRecorder:
    """Records step-by-step agent decisions, reasoning, inputs, and outputs."""
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or f"run_{int(time.time() * 1000)}"
        self.steps: List[Dict[str, Any]] = []
        self.start_time = time.time()

    def add_step(
        self,
        agent_name: str,
        action: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        decision_notes: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        step_data = {
            "step_number": len(self.steps) + 1,
            "agent": agent_name,
            "action": action,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_ms": duration_ms or 0.0,
            "inputs": inputs,
            "outputs": outputs,
            "decision_notes": decision_notes or ""
        }
        self.steps.append(step_data)
        
        # If LangSmith is active, log run step directly to project
        if _langsmith_enabled and _langsmith_client:
            try:
                _langsmith_client.create_run(
                    name=f"{agent_name}: {action}",
                    run_type="chain",
                    inputs=inputs,
                    outputs=outputs,
                    extra={"metadata": {"decision_notes": decision_notes or "", "duration_ms": duration_ms or 0.0}},
                    project_name=settings.LANGCHAIN_PROJECT or "asterline-ai-assistant"
                )
            except Exception as e:
                pass

    def get_trace(self) -> List[Dict[str, Any]]:
        return self.steps

    def get_summary(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "total_steps": len(self.steps),
            "total_duration_ms": round((time.time() - self.start_time) * 1000, 2),
            "agents_involved": list(set(s["agent"] for s in self.steps)),
            "langsmith_project": settings.LANGCHAIN_PROJECT if _langsmith_enabled else None
        }
