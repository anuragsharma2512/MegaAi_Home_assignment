import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agents.meta import MetaPromptAgent
from app.api.schemas import PromptDecisionRequest, QueryRequest
from app.core.orchestrator import Orchestrator
from app.db.models import EvalCaseResult, EvalRun, Job, PromptRewrite, PromptVersion, TraceEvent
from app.db.session import get_db
from app.eval.harness import EvaluationHarness

router = APIRouter()


@router.post("/query", summary="Submit a query and stream real-time SSE agent activity")
def submit_query(request: QueryRequest, db: Session = Depends(get_db)):
    job = Job(query=request.query, status="created")
    db.add(job)
    db.commit()
    db.refresh(job)

    def generate():
        orchestrator = Orchestrator(db, job)
        for event in orchestrator.stream():
            yield f"event: {event['event']}\ndata: {event['data']}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/trace/{job_id}", summary="Retrieve full ordered execution trace for a completed job")
def get_trace(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error_code": "JOB_NOT_FOUND", "message": "No job exists with that ID.", "job_id": job_id})
    events = db.query(TraceEvent).filter_by(job_id=job_id).order_by(TraceEvent.sequence).all()
    return {
        "job": {"id": job.id, "status": job.status, "query": job.query, "final_answer": job.final_answer, "error_code": job.error_code},
        "events": [
            {
                "sequence": e.sequence,
                "timestamp": e.timestamp,
                "agent_id": e.agent_id,
                "event_type": e.event_type,
                "input_hash": e.input_hash,
                "output_hash": e.output_hash,
                "latency_ms": e.latency_ms,
                "token_count": e.token_count,
                "policy_violations": e.policy_violations,
                "payload": e.payload,
            }
            for e in events
        ],
    }


@router.get("/eval/latest", summary="Retrieve latest eval run summary by category and scoring dimension")
def latest_eval(db: Session = Depends(get_db)):
    run = db.query(EvalRun).order_by(desc(EvalRun.created_at)).first()
    if not run:
        harness = EvaluationHarness(db)
        run = harness.run()
        MetaPromptAgent().propose_rewrite(db, run)
    return {"eval_run_id": run.id, "status": run.status, "created_at": run.created_at, "summary": run.summary, "diff": run.diff}


@router.post("/prompt-rewrites/{rewrite_id}/decision", summary="Approve or reject a pending prompt rewrite")
def decide_prompt_rewrite(rewrite_id: str, request: PromptDecisionRequest, db: Session = Depends(get_db)):
    rewrite = db.get(PromptRewrite, rewrite_id)
    if not rewrite:
        return JSONResponse(status_code=404, content={"error_code": "REWRITE_NOT_FOUND", "message": "No prompt rewrite exists with that ID.", "job_id": None})
    if rewrite.status != "pending":
        return JSONResponse(status_code=409, content={"error_code": "REWRITE_ALREADY_DECIDED", "message": "Rewrite has already been decided.", "job_id": None})
    rewrite.status = request.decision
    if request.decision == "approved":
        current = db.query(PromptVersion).filter_by(agent_id=rewrite.agent_id, active=True).first()
        next_version = (current.version + 1) if current else 1
        if current:
            current.active = False
        db.add(PromptVersion(agent_id=rewrite.agent_id, version=next_version, prompt_text=rewrite.new_prompt, active=True))
    db.commit()
    return {"rewrite_id": rewrite.id, "status": rewrite.status, "agent_id": rewrite.agent_id, "reviewer": request.reviewer, "reason": request.reason}


@router.post("/eval/targeted", summary="Trigger targeted re-eval on previously failed cases using latest approved prompts")
def targeted_eval(db: Session = Depends(get_db)):
    latest = db.query(EvalRun).order_by(desc(EvalRun.created_at)).first()
    failed_case_ids = []
    if latest:
        failed_case_ids = [r.case_id for r in db.query(EvalCaseResult).filter_by(eval_run_id=latest.id, passed=False).all()]
    harness = EvaluationHarness(db)
    run = harness.run(case_ids=failed_case_ids or None, baseline_run=latest)
    rewrite = db.query(PromptRewrite).filter_by(status="approved").order_by(desc(PromptRewrite.created_at)).first()
    if rewrite:
        rewrite.performance_delta = run.diff
        db.commit()
    MetaPromptAgent().propose_rewrite(db, run)
    return {"eval_run_id": run.id, "rerun_case_ids": failed_case_ids, "summary": run.summary, "diff": run.diff}
