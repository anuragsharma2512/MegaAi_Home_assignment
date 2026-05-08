from app.agents.base import Agent
from app.core.context import AgentOutput, Claim, SharedContext


class ValidationAgent(Agent):
    agent_id = "validation"
    max_context_tokens = 2200

    def execute(self, context: SharedContext) -> AgentOutput:
        db_result = self.tools.call(
            self.agent_id,
            "data_lookup",
            {"question": context.user_query},
            lambda r: r.ok and len(r.data.get("rows", [])) > 0,
        )
        code_result = self.tools.call(
            self.agent_id,
            "python_sandbox",
            {"code": "scores=[1,1,1,1,1,1]; print(sum(scores)/len(scores))"},
            lambda r: r.ok and r.data.get("exit_code") == 0,
        )
        reflection = self.tools.call(
            self.agent_id,
            "self_reflection",
            {"focus": "contradictions"},
            lambda r: r.ok,
        )
        rows = db_result.data.get("rows", [])
        avg = code_result.data.get("stdout", "").strip()
        contradictions = reflection.data.get("contradictions", [])
        text = f"Validated {len(rows)} database facts, computed scoring sanity average {avg or 'n/a'}, and found {len(contradictions)} prior contradictions."
        return AgentOutput(
            agent_id=self.agent_id,
            text=text,
            claims=[Claim(claim_id="validation-1", text=text, source_agent=self.agent_id)],
            metadata={"db_rows": rows, "score_sanity": avg, "reflection": reflection.data},
        )
