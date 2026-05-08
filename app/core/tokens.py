import re


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def estimate_tokens(text: str) -> int:
    return max(1, len(TOKEN_RE.findall(text or "")))
