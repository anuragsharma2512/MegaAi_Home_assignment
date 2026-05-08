import io
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import traceback
from contextlib import redirect_stderr, redirect_stdout

from app.core.config import get_settings
from app.tools.contracts import FailureMode, ToolResult


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _run(code: str) -> dict:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = 0
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(code, {"__builtins__": SAFE_BUILTINS}, {})
    except Exception:
        exit_code = 1
        stderr.write(traceback.format_exc(limit=4))
    return {"stdout": stdout.getvalue(), "stderr": stderr.getvalue(), "exit_code": exit_code}


def python_sandbox(payload: dict) -> ToolResult:
    code = payload.get("code")
    if not isinstance(code, str) or not code.strip():
        return ToolResult(ok=False, failure_mode=FailureMode.MALFORMED_INPUT, message="code must be a non-empty string")
    if "import os" in code or "__" in code:
        return ToolResult(ok=False, failure_mode=FailureMode.MALFORMED_INPUT, message="unsafe token rejected")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run, code)
        try:
            result = future.result(timeout=get_settings().python_sandbox_timeout_seconds)
        except TimeoutError:
            future.cancel()
            return ToolResult(ok=False, failure_mode=FailureMode.TIMEOUT, message="python execution timed out")
    if result["exit_code"] != 0:
        return ToolResult(ok=False, data=result, failure_mode=FailureMode.EXECUTION_ERROR, message="snippet failed")
    return ToolResult(ok=True, data=result)
