"""Bounded JSONL event writer and resumable poll-based tailer."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from .core import redact, validate_envelope


class JsonlWriter:
    def __init__(self, path: str | os.PathLike[str], *, capture_content: bool = False) -> None:
        self.path = Path(path)
        self.capture_content = capture_content
        self._lock = threading.Lock()

    def write(self, event: Mapping[str, Any]) -> int:
        validate_envelope(event)
        safe = redact(event, capture_content=self.capture_content)
        line = json.dumps(safe, separators=(",", ":"), ensure_ascii=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8", newline="\n") as handle:
            offset = handle.tell()
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        return offset


class JsonlTailer:
    """Poll complete JSONL records without interpreting partial trailing data."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        offset: int = 0,
        max_line_bytes: int = 1_048_576,
    ) -> None:
        self.path = Path(path)
        self.offset = offset
        self.max_line_bytes = max_line_bytes

    def poll(self) -> Iterator[tuple[int, dict[str, Any]]]:
        if not self.path.exists():
            return
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            while True:
                start = handle.tell()
                raw = handle.readline(self.max_line_bytes + 1)
                if not raw:
                    break
                if len(raw) > self.max_line_bytes:
                    raise ValueError(f"JSONL record at offset {start} exceeds limit")
                if not raw.endswith(b"\n"):
                    break
                value = json.loads(raw.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError(f"JSONL record at offset {start} is not an object")
                self.offset = handle.tell()
                yield start, value
