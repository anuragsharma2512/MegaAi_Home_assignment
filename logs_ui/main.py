from fastapi import FastAPI, Query
from sqlalchemy.orm import Session

from app.db.models import TraceEvent
from app.db.session import SessionLocal

app = FastAPI(title="Lightweight Log Query Interface")


@app.get("/")
def logs(job_id: str | None = Query(default=None), agent_id: str | None = Query(default=None), event_type: str | None = Query(default=None)):
    db: Session = SessionLocal()
    try:
        query = db.query(TraceEvent)
        if job_id:
            query = query.filter_by(job_id=job_id)
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        if event_type:
            query = query.filter_by(event_type=event_type)
        rows = query.order_by(TraceEvent.timestamp.desc()).limit(200).all()
        return [
            {
                "timestamp": row.timestamp,
                "job_id": row.job_id,
                "sequence": row.sequence,
                "agent_id": row.agent_id,
                "event_type": row.event_type,
                "input_hash": row.input_hash,
                "output_hash": row.output_hash,
                "latency_ms": row.latency_ms,
                "token_count": row.token_count,
                "policy_violations": row.policy_violations,
                "payload": row.payload,
            }
            for row in rows
        ]
    finally:
        db.close()
