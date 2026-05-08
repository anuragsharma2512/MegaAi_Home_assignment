from fastapi.testclient import TestClient

from app.db.init_db import init_db
from app.main import app


def test_trace_endpoint_missing_job_has_machine_error():
    init_db()
    client = TestClient(app)
    response = client.get("/trace/missing")
    assert response.status_code == 404
    assert response.json()["error_code"] == "JOB_NOT_FOUND"


def test_query_stream_completes():
    init_db()
    client = TestClient(app)
    with client.stream("POST", "/query", json={"query": "Explain RAG citations with FastAPI streaming"}) as response:
        body = "".join(response.iter_text())
    assert response.status_code == 200
    assert "event: completed" in body
    assert "retrieval" in body


def test_eval_latest_creates_summary():
    init_db()
    client = TestClient(app)
    response = client.get("/eval/latest")
    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "overall" in payload["summary"]
