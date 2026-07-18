from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEY = re.compile(
    r"(^|_)(api_?key|authorization|cookie|credential|password|private_?key|refresh_?token|secret|session|token)($|_)",
    re.IGNORECASE,
)
SENSITIVE_NORMALIZED_KEYS = {
    "accesstoken",
    "apikey",
    "authorization",
    "clientsecret",
    "cookie",
    "credential",
    "password",
    "privatekey",
    "refreshtoken",
    "secret",
    "session",
    "token",
}
SECRET_VALUE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._~+/-]{12,}|-----BEGIN [A-Z ]+PRIVATE KEY-----)",
    re.IGNORECASE,
)


def redact(value: Any, *, capture_content: bool = False) -> Any:
    """Return a JSON-compatible redacted copy before persistence or logging."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized_key = re.sub(r"[^a-z0-9]", "", key.casefold())
            if SENSITIVE_KEY.search(key) or normalized_key in SENSITIVE_NORMALIZED_KEYS:
                result[key] = "[REDACTED]"
            elif not capture_content and key.lower() in {
                "prompt",
                "completion",
                "tool_input",
                "tool_output",
                "content",
            }:
                result[key] = "[CONTENT_CAPTURE_DISABLED]"
            else:
                result[key] = redact(item, capture_content=capture_content)
        return result
    if isinstance(value, list):
        return [redact(item, capture_content=capture_content) for item in value]
    if isinstance(value, tuple):
        return [redact(item, capture_content=capture_content) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE.sub("[REDACTED]", value)[:100_000]
    return value
