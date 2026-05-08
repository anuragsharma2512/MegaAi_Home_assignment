from app.agents.base import Agent
from app.core.context import AgentOutput, Claim, SharedContext


class CritiqueAgent(Agent):
    agent_id = "critique"
    max_context_tokens = 2600

    def execute(self, context: SharedContext) -> AgentOutput:
        critiques = []
        for output in context.agent_outputs:
            for claim in output.claims:
                lower = claim.text.lower()
                confidence = 0.86
                disagreement = None
                if "ignore previous" in lower or "override" in lower:
                    confidence = 0.2
                    disagreement = "Prompt-injection-like span should not be trusted."
                if "always" in lower or "guarantee" in lower:
                    confidence = min(confidence, 0.55)
                    disagreement = disagreement or "Overconfident absolute wording."
                critiques.append(
                    {
                        "claim_id": claim.claim_id,
                        "span": claim.text[:180],
                        "confidence": confidence,
                        "disagrees": disagreement is not None,
                        "reason": disagreement or "Claim is consistent with available evidence.",
                    }
                )
        context.critiques.extend(critiques)
        flagged = [c for c in critiques if c["disagrees"]]
        text = f"Reviewed {len(critiques)} claims and flagged {len(flagged)} specific spans for revision."
        return AgentOutput(
            agent_id=self.agent_id,
            text=text,
            claims=[Claim(claim_id="critique-1", text=text, source_agent=self.agent_id)],
            metadata={"claim_scores": critiques},
        )
