from app.agents.base import Agent
from app.core.context import AgentOutput, Claim, SharedContext


class DecompositionAgent(Agent):
    agent_id = "decomposition"
    max_context_tokens = 1800

    def execute(self, context: SharedContext) -> AgentOutput:
        query = context.user_query
        tasks = [
            {"id": "t1", "type": "intent_analysis", "description": "Identify user intent and ambiguity.", "depends_on": []},
            {"id": "t2", "type": "retrieval", "description": "Gather at least two evidence chunks.", "depends_on": ["t1"]},
            {"id": "t3", "type": "tool_validation", "description": "Use database/code/reflection tools if query asks for facts, computation, or consistency.", "depends_on": ["t1"]},
            {"id": "t4", "type": "critique", "description": "Critique spans from all prior outputs.", "depends_on": ["t2", "t3"]},
            {"id": "t5", "type": "synthesis", "description": "Resolve contradictions and produce sourced answer.", "depends_on": ["t4"]},
        ]
        if any(term in query.lower() for term in ["ambiguous", "maybe", "should i", "compare", "unclear"]):
            tasks.insert(1, {"id": "t1b", "type": "clarification_inference", "description": "Infer plausible interpretations without asking extra questions.", "depends_on": ["t1"]})
            tasks[2]["depends_on"] = ["t1b"]
        context.sub_tasks = tasks
        text = "Created a dependency graph with retrieval and validation gated behind intent analysis, and synthesis gated behind critique."
        return AgentOutput(
            agent_id=self.agent_id,
            text=text,
            claims=[Claim(claim_id="decomp-1", text=text, source_agent=self.agent_id)],
            metadata={"dependency_graph": tasks},
        )
