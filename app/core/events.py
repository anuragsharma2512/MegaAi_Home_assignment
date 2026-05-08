import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.hashing import stable_hash
from app.core.tokens import estimate_tokens
from app.db.models import TraceEvent


class EventLogger:
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id

    def _next_sequence(self) -> int:
        current = self.db.query(func.max(TraceEvent.sequence)).filter_by(job_id=self.job_id).scalar()
        return int(current or 0) + 1

    def emit(
        self,
        agent_id: str,
        event_type: str,
        payload: dict[str, Any],
        input_payload: Any | None = None,
        output_payload: Any | None = None,
        latency_ms: float = 0.0,
        policy_violations: list[str] | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            job_id=self.job_id,
            sequence=self._next_sequence(),
            agent_id=agent_id,
            event_type=event_type,
            input_hash=stable_hash(input_payload if input_payload is not None else payload),
            output_hash=stable_hash(output_payload if output_payload is not None else payload),
            latency_ms=latency_ms,
            token_count=estimate_tokens(str(output_payload if output_payload is not None else payload)),
            policy_violations=policy_violations or [],
            payload=payload,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    @contextmanager
    def timed(self, agent_id: str, event_type: str, input_payload: Any) -> Iterator[dict[str, Any]]:
        started = time.perf_counter()
        result: dict[str, Any] = {}
        yield result
        latency = (time.perf_counter() - started) * 1000
        self.emit(
            agent_id=agent_id,
            event_type=event_type,
            payload=result,
            input_payload=input_payload,
            output_payload=result,
            latency_ms=latency,
        )
