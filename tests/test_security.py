from __future__ import annotations

from asterism_api.security import redact


def test_redaction_removes_secret_keys_and_values() -> None:
    result = redact(
        {
            "api_key": "not-a-real-secret",
            "nested": {
                "authorization": "Bearer abcdefghijklmnop",
                "safe": "sk-abcdefghijklmnopqrstuvwxyz",
            },
            "prompt": "sensitive analytical question",
        },
        capture_content=False,
    )
    assert result["api_key"] == "[REDACTED]"
    assert result["nested"]["authorization"] == "[REDACTED]"
    assert result["nested"]["safe"] == "[REDACTED]"
    assert result["prompt"] == "[CONTENT_CAPTURE_DISABLED]"


def test_redaction_keeps_non_sensitive_structure() -> None:
    assert redact({"title": "Safe", "count": 3}) == {"title": "Safe", "count": 3}
