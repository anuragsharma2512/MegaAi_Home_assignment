import hashlib
import json
from typing import Any


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
