from app.agents.base import Agent
from app.core.context import AgentOutput, Claim, RetrievedChunk, SharedContext


class RetrievalAgent(Agent):
    agent_id = "retrieval"
    max_context_tokens = 2200

    def execute(self, context: SharedContext) -> AgentOutput:
        result = self.tools.call(
            self.agent_id,
            "web_search",
            {"query": context.user_query},
            lambda r: r.ok and len(r.data.get("results", [])) >= 2,
        )
        chunks = []
        for idx, item in enumerate(result.data.get("results", [])[:3], start=1):
            chunk = RetrievedChunk(
                chunk_id=f"chunk-{idx}",
                source_url=item["url"],
                title=item["title"],
                text=item["snippet"],
                relevance=item["relevance"],
            )
            chunks.append(chunk)
            context.retrieved_chunks.append(chunk)
        if len(chunks) < 2:
            fallback = [
                RetrievedChunk(chunk_id="chunk-fallback-1", source_url="local://requirements", title="System Requirements", text="The system requires multi-agent orchestration, evaluation, SSE, and database-backed traces.", relevance=0.5),
                RetrievedChunk(chunk_id="chunk-fallback-2", source_url="local://architecture", title="Architecture Notes", text="A robust pipeline separates decomposition, retrieval, critique, synthesis, tools, and prompt review.", relevance=0.5),
            ]
            context.retrieved_chunks.extend(fallback)
            chunks = fallback

        text = (
            f"Multi-hop answer basis: {chunks[0].text} This is combined with {chunks[1].text} "
            "to ground the response in both implementation behavior and reliability constraints."
        )
        return AgentOutput(
            agent_id=self.agent_id,
            text=text,
            claims=[
                Claim(claim_id="retrieval-1", text=chunks[0].text, source_agent=self.agent_id, source_chunks=[chunks[0].chunk_id]),
                Claim(claim_id="retrieval-2", text=chunks[1].text, source_agent=self.agent_id, source_chunks=[chunks[1].chunk_id]),
            ],
            citations={"sentence-1": [chunks[0].chunk_id], "sentence-2": [chunks[1].chunk_id]},
            metadata={"multi_hop_chunks": [c.chunk_id for c in chunks[:2]]},
        )
