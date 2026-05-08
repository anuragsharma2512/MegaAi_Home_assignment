from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="created")
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    events: Mapped[list["TraceEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    tool_calls: Mapped[list["ToolCall"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    agent_id: Mapped[str] = mapped_column(String(80), default="system", index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    input_hash: Mapped[str] = mapped_column(String(64), default="")
    output_hash: Mapped[str] = mapped_column(String(64), default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    policy_violations: Mapped[list] = mapped_column(JSON, default=list)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    job: Mapped[Job] = relationship(back_populates="events")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(80), index=True)
    tool_name: Mapped[str] = mapped_column(String(80), index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_mode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="tool_calls")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    prompt_text: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    diff: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvalCaseResult(Base):
    __tablename__ = "eval_case_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eval_run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id"), index=True)
    case_id: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    query: Mapped[str] = mapped_column(Text)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    prompts: Mapped[dict] = mapped_column(JSON, default=dict)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    scores: Mapped[dict] = mapped_column(JSON, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PromptRewrite(Base):
    __tablename__ = "prompt_rewrites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    eval_run_id: Mapped[str] = mapped_column(String(36), index=True)
    agent_id: Mapped[str] = mapped_column(String(80), index=True)
    old_prompt: Mapped[str] = mapped_column(Text)
    new_prompt: Mapped[str] = mapped_column(Text)
    structured_diff: Mapped[dict] = mapped_column(JSON, default=dict)
    justification: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    performance_delta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
