from sqlalchemy.orm import Session

from app.core.orchestrator import Orchestrator
from app.db.models import EvalCaseResult, EvalRun, Job, PromptVersion
from app.eval.cases import EVAL_CASES
from app.eval.scoring import score_case, summarize


class EvaluationHarness:
    def __init__(self, db: Session):
        self.db = db

    def run(self, case_ids: list[str] | None = None, baseline_run: EvalRun | None = None) -> EvalRun:
        selected = [c for c in EVAL_CASES if case_ids is None or c["id"] in case_ids]
        results = []
        run = EvalRun(status="running", summary={}, diff={})
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        active_prompts = {p.agent_id: p.prompt_text for p in self.db.query(PromptVersion).filter_by(active=True).all()}
        for case in selected:
            job = Job(query=case["query"], status="created")
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            context = Orchestrator(self.db, job).run_to_completion()
            scores, passed = score_case(case, context)
            tool_calls = [obs.model_dump() for obs in context.tool_observations]
            outputs = {out.agent_id: out.model_dump() for out in context.agent_outputs}
            row = EvalCaseResult(
                eval_run_id=run.id,
                case_id=case["id"],
                category=case["category"],
                query=case["query"],
                job_id=job.id,
                prompts=active_prompts,
                tool_calls=tool_calls,
                outputs=outputs,
                scores=scores,
                passed=passed,
            )
            self.db.add(row)
            result = {"case_id": case["id"], "category": case["category"], "scores": scores, "passed": passed}
            results.append(result)
        run.status = "completed"
        run.summary = summarize(results) if results else {}
        run.diff = self._diff_against_baseline(results, baseline_run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _diff_against_baseline(self, results: list[dict], baseline_run: EvalRun | None) -> dict:
        if baseline_run is None:
            return {"baseline_eval_run_id": None, "deltas": []}
        baseline_rows = {r.case_id: r for r in self.db.query(EvalCaseResult).filter_by(eval_run_id=baseline_run.id).all()}
        deltas = []
        for result in results:
            old = baseline_rows.get(result["case_id"])
            if not old:
                continue
            for dimension, score in result["scores"].items():
                old_score = old.scores.get(dimension, {}).get("score", 0)
                deltas.append(
                    {
                        "case_id": result["case_id"],
                        "dimension": dimension,
                        "before": old_score,
                        "after": score["score"],
                        "delta": round(score["score"] - old_score, 3),
                    }
                )
        return {"baseline_eval_run_id": baseline_run.id, "deltas": deltas}
