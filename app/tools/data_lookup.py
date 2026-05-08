import re

import sqlparse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.tools.contracts import FailureMode, ToolResult


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_facts (
  id SERIAL PRIMARY KEY,
  subject TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object TEXT NOT NULL,
  source_url TEXT NOT NULL
);
"""

SEED_FACTS = [
    ("fastapi", "supports", "server-sent event streaming through streaming responses", "https://fastapi.tiangolo.com/"),
    ("postgresql", "stores", "durable evaluation and trace records", "https://www.postgresql.org/"),
    ("rag", "requires", "retrieved chunks and citations for grounded answers", "https://arxiv.org/abs/2005.11401"),
    ("prompt injection", "attacks", "instruction hierarchy and tool trust boundaries", "https://owasp.org/www-project-top-10-for-large-language-model-applications/"),
]


def ensure_knowledge_seeded(db: Session) -> None:
    db.execute(text(SCHEMA_SQL))
    count = db.execute(text("SELECT COUNT(*) FROM knowledge_facts")).scalar()
    if count == 0:
        for row in SEED_FACTS:
            db.execute(
                text("INSERT INTO knowledge_facts (subject, predicate, object, source_url) VALUES (:s, :p, :o, :u)"),
                {"s": row[0], "p": row[1], "o": row[2], "u": row[3]},
            )
    db.commit()


def nl_to_sql(question: str) -> str:
    normalized = question.lower()
    terms = re.findall(r"[a-z][a-z0-9 -]{2,}", normalized)
    interesting = [t.strip() for t in terms if t.strip() in {"fastapi", "postgresql", "rag", "prompt injection"}]
    if interesting:
        clauses = " OR ".join([f"subject LIKE '%{term}%'" for term in interesting])
    else:
        clauses = "subject LIKE '%' OR object LIKE '%evaluation%'"
    return f"SELECT subject, predicate, object, source_url FROM knowledge_facts WHERE {clauses} LIMIT 5"


def data_lookup(payload: dict, db: Session) -> ToolResult:
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return ToolResult(ok=False, failure_mode=FailureMode.MALFORMED_INPUT, message="question must be a non-empty string")
    if "timeout" in question.lower():
        return ToolResult(ok=False, failure_mode=FailureMode.TIMEOUT, message="simulated database timeout")

    ensure_knowledge_seeded(db)
    sql = nl_to_sql(question)
    parsed = sqlparse.parse(sql)
    if not parsed or parsed[0].get_type() != "SELECT":
        return ToolResult(ok=False, failure_mode=FailureMode.MALFORMED_INPUT, message="only SELECT statements are allowed")
    rows = db.execute(text(sql)).mappings().all()
    if not rows:
        return ToolResult(ok=False, failure_mode=FailureMode.EMPTY_RESULTS, data={"sql": sql}, message="no rows")
    return ToolResult(ok=True, data={"sql": sql, "rows": [dict(r) for r in rows]})
