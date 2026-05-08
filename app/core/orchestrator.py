import json
import time
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.agents.critique import CritiqueAgent
from app.agents.decomposition import DecompositionAgent
from app.agents.retrieval import RetrievalAgent
from app.agents.synthesis import SynthesisAgent
from app.agents.validation import ValidationAgent
from app.core.context import ContextBudgetManager, SharedContext
from app.core.events import EventLogger
from app.db.models import Job
from app.tools.registry import ToolRegistry


class Orchestrator:
    agent_id = "orchestrator"

    def __init__(self, db: Session, job: Job):
        self.db = db
        self.job = job
        self.context = SharedContext(job_id=job.id, user_query=job.query)
        self.logger = EventLogger(db, job.id)
        self.budget = ContextBudgetManager(self.context)
        self.tools = ToolRegistry(db, job.id, self.context)
        self.agents = {
            "decomposition": DecompositionAgent(self.logger, self.tools, self.budget),
            "retrieval": RetrievalAgent(self.logger, self.tools, self.budget),
            "validation": ValidationAgent(self.logger, self.tools, self.budget),
            "critique": CritiqueAgent(self.logger, self.tools, self.budget),
            "synthesis": SynthesisAgent(self.logger, self.tools, self.budget),
        }

    def stream(self) -> Generator[dict, None, SharedContext]:
        self.job.status = "running"
        self.db.commit()
        yield self._event("job_started", "system", {"job_id": self.job.id})
        try:
            for agent_id in self._decide_route():
                justification = self._route_justification(agent_id)
                self.context.route_plan.append({"agent_id": agent_id, "justification": justification})
                self.logger.emit(self.agent_id, "routing_decision", {"next_agent": agent_id, "justification": justification, "remaining_budget": self.budget.remaining(agent_id)})
                yield self._event("routing_decision", self.agent_id, {"next_agent": agent_id, "justification": justification})
                yield self._event("agent_started", agent_id, {"context_tokens": self.context.token_count()})
                started = time.perf_counter()
                output = self.agents[agent_id].run(self.context)
                latency = (time.perf_counter() - started) * 1000
                for token in output.text.split():
                    yield self._event("token", agent_id, {"token": token + " ", "remaining_budget": self.budget.remaining(agent_id)})
                yield self._event("agent_completed", agent_id, {"latency_ms": latency, "metadata": output.metadata})

            self.job.final_answer = self.context.final_answer
            self.job.status = "completed"
            self.db.commit()
            self.logger.emit("system", "job_completed", {"final_answer": self.context.final_answer, "provenance_map": self.context.provenance_map})
            yield self._event("completed", "system", {"job_id": self.job.id, "final_answer": self.context.final_answer, "provenance_map": self.context.provenance_map})
            return self.context
        except Exception as exc:
            self.job.status = "failed"
            self.job.error_code = "ORCHESTRATION_FAILED"
            self.job.error_message = str(exc)
            self.db.commit()
            self.logger.emit("system", "job_failed", {"error": str(exc)})
            yield self._event("error", "system", {"error_code": "ORCHESTRATION_FAILED", "message": str(exc), "job_id": self.job.id})
            return self.context

    def run_to_completion(self) -> SharedContext:
        final_context = self.context
        gen = self.stream()
        while True:
            try:
                next(gen)
            except StopIteration as done:
                if done.value is not None:
                    final_context = done.value
                break
        return final_context

    def _decide_route(self) -> list[str]:
        query = self.job.query.lower()
        route = ["decomposition", "retrieval"]
        if any(term in query for term in ["calculate", "sql", "database", "tool", "eval", "trace", "contradiction", "prompt", "docker"]):
            route.append("validation")
        else:
            route.append("validation")
        route.extend(["critique", "synthesis"])
        return route

    def _route_justification(self, agent_id: str) -> str:
        justifications = {
            "decomposition": "First, create typed subtasks and dependency graph before any downstream work.",
            "retrieval": "Evidence is needed before claims can be critiqued or synthesized.",
            "validation": "Tool-backed validation checks structured facts, executable scoring logic, and prior contradictions.",
            "critique": "All prior claims must receive span-level confidence scoring before final output.",
            "synthesis": "Only after critique can contradictions be resolved into a provenance-mapped answer.",
        }
        return justifications[agent_id]

    def _event(self, event_type: str, agent_id: str, data: dict) -> dict:
        return {"event": event_type, "data": json.dumps({"agent_id": agent_id, **data}, default=str)}
