from app.tools.contracts import FailureMode, ToolResult


CORPUS = [
    {
        "title": "FastAPI Streaming Responses",
        "url": "https://fastapi.tiangolo.com/advanced/custom-response/",
        "snippet": "FastAPI can stream incremental responses to clients using StreamingResponse and SSE-compatible event formats.",
        "keywords": {"fastapi", "stream", "sse", "api"},
    },
    {
        "title": "PostgreSQL Reliability",
        "url": "https://www.postgresql.org/docs/current/transaction-iso.html",
        "snippet": "PostgreSQL transactions and isolation levels support durable audit storage for reproducible evaluation runs.",
        "keywords": {"postgres", "database", "sql", "audit", "reproducible"},
    },
    {
        "title": "Prompt Injection Failure Modes",
        "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
        "snippet": "Prompt injection attempts can ask a model to ignore prior instructions, leak data, or trust unverified premises.",
        "keywords": {"prompt", "injection", "adversarial", "robustness", "security"},
    },
    {
        "title": "Retrieval Augmented Generation",
        "url": "https://arxiv.org/abs/2005.11401",
        "snippet": "Retrieval-augmented generation conditions answers on retrieved passages and should cite evidence used in generation.",
        "keywords": {"rag", "retrieval", "citation", "chunks", "multi-hop"},
    },
]


def web_search(payload: dict) -> ToolResult:
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        return ToolResult(ok=False, failure_mode=FailureMode.MALFORMED_INPUT, message="query must be a non-empty string")
    if "timeout" in query.lower():
        return ToolResult(ok=False, failure_mode=FailureMode.TIMEOUT, message="simulated search timeout")

    terms = set(query.lower().replace("-", " ").split())
    results = []
    for item in CORPUS:
        overlap = len(terms & item["keywords"])
        if overlap:
            results.append(
                {
                    "title": item["title"],
                    "url": item["url"],
                    "snippet": item["snippet"],
                    "relevance": min(1.0, 0.35 + overlap * 0.2),
                }
            )
    results.sort(key=lambda r: r["relevance"], reverse=True)
    if not results:
        return ToolResult(ok=False, failure_mode=FailureMode.EMPTY_RESULTS, message="no matching documents")
    return ToolResult(ok=True, data={"results": results[:5]})
