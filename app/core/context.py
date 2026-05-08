from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.tokens import estimate_tokens


class Claim(BaseModel):
    claim_id: str
    text: str
    source_agent: str
    source_chunks: list[str] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    chunk_id: str
    source_url: str
    title: str
    text: str
    relevance: float


class ToolObservation(BaseModel):
    tool_name: str
    input_payload: dict
    output_payload: dict
    accepted: bool
    failure_mode: str | None = None


class AgentOutput(BaseModel):
    agent_id: str
    text: str
    claims: list[Claim] = Field(default_factory=list)
    citations: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class SharedContext(BaseModel):
    job_id: str
    user_query: str
    route_plan: list[dict] = Field(default_factory=list)
    sub_tasks: list[dict] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    tool_observations: list[ToolObservation] = Field(default_factory=list)
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    critiques: list[dict] = Field(default_factory=list)
    final_answer: str | None = None
    provenance_map: list[dict] = Field(default_factory=list)
    policy_violations: list[dict] = Field(default_factory=list)
    summaries: list[dict] = Field(default_factory=list)

    def visible_text(self) -> str:
        return self.model_dump_json(exclude_none=True)

    def token_count(self) -> int:
        return estimate_tokens(self.visible_text())


class ContextBudgetManager:
    def __init__(self, context: SharedContext):
        self.context = context
        self.agent_budgets: dict[str, int] = {}
        self.agent_usage: dict[str, int] = {}

    def declare_budget(self, agent_id: str, max_tokens: int) -> None:
        self.agent_budgets[agent_id] = max_tokens
        self.agent_usage[agent_id] = self.context.token_count()

    def remaining(self, agent_id: str) -> int:
        budget = self.agent_budgets.get(agent_id, 0)
        used = self.context.token_count()
        return budget - used

    def assert_within_budget(self, agent_id: str) -> list[str]:
        budget = self.agent_budgets.get(agent_id)
        if budget is None:
            return [f"{agent_id} executed without declaring context budget"]
        used = self.context.token_count()
        self.agent_usage[agent_id] = used
        if used > budget:
            violation = f"{agent_id} exceeded context budget: used={used}, budget={budget}"
            self.context.policy_violations.append({"agent_id": agent_id, "violation": violation})
            return [violation]
        return []

    def compress_if_needed(self, agent_id: str, compression_agent: "CompressionAgent") -> bool:
        budget = self.agent_budgets.get(agent_id)
        if budget is None or self.context.token_count() <= budget:
            return False
        compression_agent.compress(self.context)
        return True
