from abc import ABC, abstractmethod

from app.core.context import AgentOutput, ContextBudgetManager, SharedContext
from app.core.events import EventLogger
from app.tools.registry import ToolRegistry


class Agent(ABC):
    agent_id: str
    max_context_tokens: int

    def __init__(self, logger: EventLogger, tools: ToolRegistry, budget: ContextBudgetManager):
        self.logger = logger
        self.tools = tools
        self.budget = budget

    def run(self, context: SharedContext) -> AgentOutput:
        self.budget.declare_budget(self.agent_id, self.max_context_tokens)
        self.budget.compress_if_needed(self.agent_id, CompressionAgent(self.logger, self.tools, self.budget))
        output = self.execute(context)
        context.agent_outputs.append(output)
        violations = self.budget.assert_within_budget(self.agent_id)
        self.logger.emit(
            self.agent_id,
            "agent_output",
            {"text": output.text, "claims": [c.model_dump() for c in output.claims], "metadata": output.metadata},
            input_payload=context.user_query,
            output_payload=output.model_dump(),
            policy_violations=violations,
        )
        return output

    @abstractmethod
    def execute(self, context: SharedContext) -> AgentOutput:
        raise NotImplementedError


class CompressionAgent:
    agent_id = "compression"

    def __init__(self, logger: EventLogger, tools: ToolRegistry, budget: ContextBudgetManager):
        self.logger = logger
        self.tools = tools
        self.budget = budget

    def compress(self, context: SharedContext) -> None:
        if len(context.agent_outputs) <= 2:
            return
        preserved = [o for o in context.agent_outputs if o.claims or o.citations]
        filler = [o for o in context.agent_outputs if not o.claims and not o.citations]
        if filler:
            summary_text = " | ".join(o.text[:120] for o in filler)
            context.summaries.append({"lossy_filler_summary": summary_text, "preserved_structured_outputs": len(preserved)})
            context.agent_outputs = preserved
            self.logger.emit("compression", "context_compressed", {"summary": summary_text, "preserved": len(preserved)})
