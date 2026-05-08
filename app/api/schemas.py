from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    job_id: str | None = None


class PromptDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reviewer: str = "human"
    reason: str = ""
