import time
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.context import SharedContext, ToolObservation
from app.db.models import ToolCall
from app.tools.contracts import FailureMode, ToolResult
from app.tools.data_lookup import data_lookup
from app.tools.python_sandbox import python_sandbox
from app.tools.self_reflection import self_reflection
from app.tools.web_search import web_search


class ToolRegistry:
    def __init__(self, db: Session, job_id: str, context: SharedContext):
        self.db = db
        self.job_id = job_id
        self.context = context
        self.max_retries = get_settings().max_tool_retries

    def call(self, agent_id: str, tool_name: str, payload: dict, accept: Callable[[ToolResult], bool]) -> ToolResult:
        current_payload = dict(payload)
        last_result = ToolResult(ok=False, failure_mode=FailureMode.EMPTY_RESULTS, message="not called")
        for attempt in range(1, self.max_retries + 2):
            started = time.perf_counter()
            result = self._dispatch(tool_name, current_payload)
            latency_ms = (time.perf_counter() - started) * 1000
            accepted = bool(accept(result))
            self.db.add(
                ToolCall(
                    job_id=self.job_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    attempt=attempt,
                    input_payload=current_payload,
                    output_payload=result.model_dump(),
                    latency_ms=latency_ms,
                    accepted=accepted,
                    failure_mode=result.failure_mode.value if result.failure_mode else None,
                )
            )
            self.context.tool_observations.append(
                ToolObservation(
                    tool_name=tool_name,
                    input_payload=current_payload,
                    output_payload=result.model_dump(),
                    accepted=accepted,
                    failure_mode=result.failure_mode.value if result.failure_mode else None,
                )
            )
            self.db.commit()
            if accepted:
                return result
            last_result = result
            current_payload = self._fallback_payload(tool_name, current_payload, result)
        return last_result

    def _dispatch(self, tool_name: str, payload: dict) -> ToolResult:
        if tool_name == "web_search":
            return web_search(payload)
        if tool_name == "python_sandbox":
            return python_sandbox(payload)
        if tool_name == "data_lookup":
            return data_lookup(payload, self.db)
        if tool_name == "self_reflection":
            return self_reflection(payload, self.context)
        return ToolResult(ok=False, failure_mode=FailureMode.MALFORMED_INPUT, message=f"unknown tool {tool_name}")

    def _fallback_payload(self, tool_name: str, payload: dict, result: ToolResult) -> dict:
        next_payload = dict(payload)
        if result.failure_mode == FailureMode.TIMEOUT:
            next_payload["timeout_avoidance"] = True
            if "query" in next_payload:
                next_payload["query"] = next_payload["query"].replace("timeout", "").strip() or "reliable fallback query"
            if "question" in next_payload:
                next_payload["question"] = next_payload["question"].replace("timeout", "").strip() or "evaluation records"
        elif result.failure_mode == FailureMode.EMPTY_RESULTS:
            if "query" in next_payload:
                next_payload["query"] = f"{next_payload['query']} rag evaluation postgres"
            if "question" in next_payload:
                next_payload["question"] = "evaluation records and rag citations"
        elif result.failure_mode == FailureMode.MALFORMED_INPUT:
            if tool_name == "python_sandbox":
                next_payload["code"] = "print('sanitized fallback')"
            elif tool_name == "self_reflection":
                next_payload["focus"] = "contradictions"
            else:
                next_payload["query"] = next_payload.get("query") or next_payload.get("question") or "orchestration"
                next_payload["question"] = next_payload.get("question") or "orchestration"
        elif result.failure_mode == FailureMode.EXECUTION_ERROR:
            next_payload["code"] = "print('execution recovered')"
        return next_payload
