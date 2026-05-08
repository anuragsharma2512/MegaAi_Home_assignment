from enum import StrEnum
from pydantic import BaseModel, Field


class FailureMode(StrEnum):
    TIMEOUT = "timeout"
    EMPTY_RESULTS = "empty_results"
    MALFORMED_INPUT = "malformed_input"
    EXECUTION_ERROR = "execution_error"


class ToolResult(BaseModel):
    ok: bool
    data: dict = Field(default_factory=dict)
    failure_mode: FailureMode | None = None
    message: str = ""
