from sqlalchemy.orm import Session

from app.db.models import Base, PromptVersion
from app.db.session import engine


DEFAULT_PROMPTS = {
    "orchestrator": "Route dynamically using task type, dependency state, tool evidence, and remaining budget. Log every routing justification.",
    "decomposition": "Break ambiguous user queries into typed subtasks with explicit dependencies and no direct agent handoffs.",
    "retrieval": "Answer only after combining at least two chunks. Cite every chunk contribution by chunk id.",
    "critique": "Score each claim independently, flag exact disputed spans, and explain disagreements.",
    "synthesis": "Merge agent outputs, resolve contradictions, and map every final sentence to agent and chunk provenance.",
    "compression": "Compress old context while preserving structured data exactly and only shortening conversational filler.",
    "meta": "Find the weakest prompt from failed eval cases and propose an auditable rewrite without auto-applying it.",
}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        for agent_id, prompt in DEFAULT_PROMPTS.items():
            exists = db.query(PromptVersion).filter_by(agent_id=agent_id, active=True).first()
            if not exists:
                db.add(PromptVersion(agent_id=agent_id, version=1, prompt_text=prompt, active=True))
        db.commit()
