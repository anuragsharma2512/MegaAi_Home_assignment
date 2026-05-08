from app.core.context import SharedContext
from app.tools.contracts import FailureMode, ToolResult


def self_reflection(payload: dict, context: SharedContext) -> ToolResult:
    focus = payload.get("focus")
    if focus is not None and not isinstance(focus, str):
        return ToolResult(ok=False, failure_mode=FailureMode.MALFORMED_INPUT, message="focus must be a string")
    outputs = [o.model_dump() for o in context.agent_outputs]
    if not outputs:
        return ToolResult(ok=False, failure_mode=FailureMode.EMPTY_RESULTS, message="no previous outputs to inspect")
    contradictions = []
    all_text = " ".join(o["text"].lower() for o in outputs)
    if "ignore" in all_text and "instruction" in all_text:
        contradictions.append({"span": "ignore ... instruction", "reason": "possible prompt injection language preserved"})
    if "must use" in all_text and "unnecessary" in all_text:
        contradictions.append({"span": "must use/unnecessary", "reason": "tool-selection inconsistency"})
    return ToolResult(ok=True, data={"outputs_seen": outputs, "contradictions": contradictions})
