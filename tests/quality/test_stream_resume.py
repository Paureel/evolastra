from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from asterism_api import api as api_module
from asterism_api.event_store import EventStore, make_event
from asterism_api.schemas import RunCreate
from sqlalchemy.orm import Session, sessionmaker


class DisconnectAfterOnePoll:
    def __init__(self, last_event_id: int) -> None:
        self.headers = {"last-event-id": str(last_event_id)}
        self.polls = 0

    async def is_disconnected(self) -> bool:
        self.polls += 1
        return self.polls > 1


async def collect(iterator: AsyncIterator[Any]) -> str:
    chunks: list[str] = []
    async for chunk in iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else str(chunk))
    return "".join(chunks)


def test_sse_resume_uses_larger_cursor_and_returns_full_ordered_events(
    session: Session,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EventStore(session)
    run, _ = store.create_run(
        RunCreate(title="Resume stream", objective="Resume after applied events", seed=29)
    )
    for index in range(1, 4):
        event = make_event(
            run_id=run.id,
            event_type="galaxy.analysis.metric.recorded.v1",
            subject=f"run/{run.id}/metric/{index}",
            data={
                "metric": {
                    "id": f"metr_{index:08x}000040008000000000000000",
                    "run_id": run.id,
                    "name": "tokens.total",
                    "value": index,
                }
            },
        )
        assert store.ingest(event.model_dump(mode="json")).accepted

    def get_poll_session() -> Iterator[Session]:
        with session_factory() as poll_session:
            yield poll_session

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(api_module, "get_session", get_poll_session)
    monkeypatch.setattr(api_module.asyncio, "sleep", no_sleep)
    request = DisconnectAfterOnePoll(last_event_id=2)
    response = asyncio.run(api_module.stream_events(run.id, request, session, after=1))
    body = asyncio.run(collect(response.body_iterator))

    frames = [frame for frame in body.strip().split("\n\n") if frame]
    assert [int(frame.splitlines()[0].removeprefix("id: ")) for frame in frames] == [3, 4]
    assert all("event: semantic" in frame for frame in frames)
    envelopes = [json.loads(frame.split("data: ", 1)[1]) for frame in frames]
    assert [envelope["sequence"] for envelope in envelopes] == [3, 4]
    assert all(envelope["runid"] == run.id for envelope in envelopes)
