from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Real-Time Multi-Agent LLM Orchestration and Evaluation System",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error_code": "VALIDATION_ERROR", "message": str(exc), "job_id": None})


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error_code": "HTTP_ERROR", "message": str(exc.detail), "job_id": None})


app.include_router(router)
