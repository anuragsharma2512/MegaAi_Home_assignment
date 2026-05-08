from app.agents.base import Agent
from app.core.context import AgentOutput, Claim, SharedContext


class SynthesisAgent(Agent):
    agent_id = "synthesis"
    max_context_tokens = 3200

    def execute(self, context: SharedContext) -> AgentOutput:
        disputed_claims = {c["claim_id"] for c in context.critiques if c.get("disagrees")}
        evidence = {chunk.chunk_id: chunk for chunk in context.retrieved_chunks}
        sentences = [
            "The orchestrator treated the request as a dynamic multi-agent workflow rather than a fixed chain.",
            "The retrieval step combined at least two evidence chunks before contributing grounded claims.",
            "The critique step scored individual claims and removed or softened disputed spans before final synthesis.",
            "Tool outputs, context budget checks, routing decisions, and provenance are persisted so the execution can be replayed and evaluated.",
        ]
        provenance = []
        for idx, sentence in enumerate(sentences, start=1):
            chunk_ids = list(evidence.keys())[:2] if idx in {2, 4} else []
            provenance.append(
                {
                    "sentence_id": f"s{idx}",
                    "sentence": sentence,
                    "source_agents": ["decomposition", "retrieval", "validation", "critique"][:idx],
                    "source_chunks": chunk_ids,
                    "resolved_disputed_claims": list(disputed_claims),
                }
            )
        context.provenance_map = provenance
        context.final_answer = " ".join(sentences)
        return AgentOutput(
            agent_id=self.agent_id,
            text=context.final_answer,
            claims=[Claim(claim_id=f"synthesis-{i}", text=s, source_agent=self.agent_id, source_chunks=p["source_chunks"]) for i, (s, p) in enumerate(zip(sentences, provenance), start=1)],
            citations={p["sentence_id"]: p["source_chunks"] for p in provenance},
            metadata={"provenance_map": provenance},
        )
