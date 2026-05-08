from difflib import ndiff

from sqlalchemy.orm import Session

from app.db.models import EvalCaseResult, EvalRun, PromptRewrite, PromptVersion


class MetaPromptAgent:
    agent_id = "meta"

    def propose_rewrite(self, db: Session, eval_run: EvalRun) -> PromptRewrite | None:
        failures = db.query(EvalCaseResult).filter_by(eval_run_id=eval_run.id, passed=False).all()
        if not failures:
            return None
        dimension_totals: dict[str, list[float]] = {}
        for failure in failures:
            for dimension, score in failure.scores.items():
                dimension_totals.setdefault(dimension, []).append(float(score["score"]))
        weakest_dimension = min(dimension_totals, key=lambda k: sum(dimension_totals[k]) / len(dimension_totals[k]))
        agent_id = {
            "citation_accuracy": "retrieval",
            "contradiction_resolution": "synthesis",
            "tool_selection_efficiency": "orchestrator",
            "context_budget_compliance": "compression",
            "critique_agreement": "critique",
        }.get(weakest_dimension, "synthesis")
        prompt = db.query(PromptVersion).filter_by(agent_id=agent_id, active=True).first()
        if prompt is None:
            return None
        old = prompt.prompt_text
        new = f"{old}\nPrioritize eval failures in {weakest_dimension}: require explicit evidence, concise reasoning, and measurable acceptance criteria."
        diff = list(ndiff(old.splitlines(), new.splitlines()))
        rewrite = PromptRewrite(
            eval_run_id=eval_run.id,
            agent_id=agent_id,
            old_prompt=old,
            new_prompt=new,
            structured_diff={"weakest_dimension": weakest_dimension, "diff": diff},
            justification=f"Failed cases had the lowest average score in {weakest_dimension}; this rewrite makes that dimension explicit.",
        )
        db.add(rewrite)
        db.commit()
        db.refresh(rewrite)
        return rewrite
