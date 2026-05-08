from collections import defaultdict

from app.core.context import SharedContext


DIMENSIONS = [
    "answer_correctness",
    "citation_accuracy",
    "contradiction_resolution",
    "tool_selection_efficiency",
    "context_budget_compliance",
    "critique_agreement",
]


def score_case(case: dict, context: SharedContext) -> tuple[dict, bool]:
    answer = (context.final_answer or "").lower()
    expected = [term.lower() for term in case.get("expected_terms", [])]
    term_hits = sum(1 for term in expected if term in answer or term in context.visible_text().lower())
    correctness = term_hits / max(1, len(expected))

    cited_sentences = [p for p in context.provenance_map if p.get("source_chunks")]
    citation_accuracy = min(1.0, len(cited_sentences) / 2)

    unresolved = [c for c in context.critiques if c.get("disagrees") and c.get("span", "").lower() in answer]
    contradiction_resolution = 1.0 if not unresolved else 0.25

    necessary = 3
    calls = len(context.tool_observations)
    tool_efficiency = max(0.0, 1.0 - max(0, calls - necessary) * 0.15)

    context_budget = 0.0 if context.policy_violations else 1.0

    critique_items = context.critiques or []
    high_conf = [c for c in critique_items if c.get("confidence", 0) >= 0.7 and not c.get("disagrees")]
    critique_agreement = len(high_conf) / max(1, len(critique_items))

    raw = {
        "answer_correctness": (correctness, f"Matched {term_hits}/{len(expected)} expected concepts: {expected}."),
        "citation_accuracy": (citation_accuracy, f"{len(cited_sentences)} final sentences include chunk provenance."),
        "contradiction_resolution": (contradiction_resolution, f"{len(unresolved)} disputed spans leaked into final answer."),
        "tool_selection_efficiency": (tool_efficiency, f"{calls} tool calls observed; expected about {necessary}."),
        "context_budget_compliance": (context_budget, f"{len(context.policy_violations)} budget policy violations logged."),
        "critique_agreement": (critique_agreement, f"{len(high_conf)}/{len(critique_items)} critiques agree with retained claims."),
    }
    scores = {dimension: {"score": round(value, 3), "justification": reason} for dimension, (value, reason) in raw.items()}
    passed = sum(item["score"] for item in scores.values()) / len(scores) >= 0.72
    return scores, passed


def summarize(results: list[dict]) -> dict:
    grouped = defaultdict(lambda: defaultdict(list))
    for result in results:
        for dimension, score in result["scores"].items():
            grouped[result["category"]][dimension].append(score["score"])
    summary = {}
    for category, dimensions in grouped.items():
        summary[category] = {
            dimension: {
                "avg_score": round(sum(values) / len(values), 3),
                "case_count": len(values),
            }
            for dimension, values in dimensions.items()
        }
    summary["overall"] = {
        dimension: {
            "avg_score": round(sum(r["scores"][dimension]["score"] for r in results) / len(results), 3),
            "case_count": len(results),
        }
        for dimension in DIMENSIONS
    }
    return summary
