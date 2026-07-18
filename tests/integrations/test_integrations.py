from __future__ import annotations

import io
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sdk" / "python"))

from galaxy_sdk import GalaxyClient, ListSink

from integrations.a2a import map_agent_card, map_task
from integrations.ag_ui import map_event as map_ag_ui
from integrations.codex_app_server import map_notification
from integrations.codex_hooks import capture_stdin, flush_once, map_hook, spool_event
from integrations.codex_sdk import map_run_result
from integrations.core import build_event, entity_payload, redact, validate_envelope
from integrations.jsonl import JsonlTailer, JsonlWriter
from integrations.openai_agents import AsterismTracingProcessor
from integrations.openlineage import export_run_event, ingest_run_event
from integrations.otlp import UnsupportedOtlpPayload, map_logs_json, map_traces_json

FIXTURES = ROOT / "examples" / "integrations" / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def assert_entity_identity(testcase: unittest.TestCase, event: dict, entity_key: str) -> dict:
    entity = event["data"][entity_key]
    testcase.assertEqual(entity["run_id"], event["runid"])
    testcase.assertEqual(entity["schema_version"], 1)
    testcase.assertIsInstance(entity["id"], str)
    return entity


class CoreTests(unittest.TestCase):
    def test_redaction_is_recursive_bounded_and_default_deny(self) -> None:
        value = {
            "apiKey": "sk-example-secret-123456789",
            "nested": {"prompt": "private prompt", "note": "Bearer abcdefghijklmnop"},
        }
        safe = redact(value)
        self.assertEqual(safe["apiKey"], "[REDACTED_SECRET]")
        self.assertEqual(safe["nested"]["prompt"], {"redacted": True, "length": 14})
        self.assertEqual(safe["nested"]["note"], "[REDACTED_SECRET]")

    def test_envelope_is_complete_and_deterministic_for_native_id(self) -> None:
        run_id = "run_123456789abc4def8abc123456789abc"
        kwargs = dict(
            event_type="galaxy.analysis.run.started.v1",
            source="urn:test",
            subject=run_id,
            run_id=run_id,
            data=entity_payload(
                "run", entity_id=run_id, run_id=run_id, status="started", title="test"
            ),
            adapter="test/1",
            native_id="native-1",
        )
        first = build_event(**kwargs)
        second = build_event(**kwargs)
        validate_envelope(first)
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotIn("sequence", first)
        self.assertRegex(first["id"], r"^evt_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")
        self.assertRegex(first["runid"], r"^run_[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")
        self.assertEqual(first["subject"], f"run/{run_id}")
        self.assertRegex(first["traceid"], r"^[0-9a-f]{32}$")
        self.assertIn("deduplication_key", first["data"]["integration"])
        configured_a = build_event(**kwargs, deduplication_key_override="shared-activity")
        configured_b = build_event(
            **{**kwargs, "native_id": "different-native-id"},
            deduplication_key_override="shared-activity",
        )
        self.assertEqual(
            configured_a["data"]["integration"]["deduplication_key"],
            configured_b["data"]["integration"]["deduplication_key"],
        )
        with self.assertRaisesRegex(ValueError, "data.run"):
            build_event(**{**kwargs, "data": {"status": "started"}})


class CodexTests(unittest.TestCase):
    def test_hook_fixture_maps_and_redacts(self) -> None:
        payload = fixture("codex_hook_session_start.json")
        payload["authorization"] = "Bearer abcdefghijklmnop"
        event = map_hook(payload)
        validate_envelope(event)
        self.assertEqual(event["type"], "galaxy.analysis.run.created.v1")
        assert_entity_identity(self, event, "run")
        self.assertTrue(event["data"]["run"]["title"].startswith("Codex ·"))
        self.assertEqual(event["data"]["run"]["status"], "created")
        self.assertEqual(event["data"]["native"]["authorization"], "[REDACTED_SECRET]")
        repeated = map_hook(payload)
        self.assertNotEqual(repeated["id"], event["id"])
        self.assertEqual(
            repeated["data"]["integration"]["deduplication_key"],
            event["data"]["integration"]["deduplication_key"],
        )
        self.assertEqual(repeated["runid"], event["runid"])

    def test_hook_semantic_entities_use_documented_ids(self) -> None:
        common = {
            "session_id": "session_fixture_002",
            "turn_id": "turn_fixture_002",
            "cwd": "/workspace/example",
            "model": "example-model",
            "permission_mode": "default",
        }
        tool = map_hook(
            {
                **common,
                "hook_event_name": "PreToolUse",
                "tool_use_id": "tool_fixture_001",
                "tool_name": "Bash",
                "tool_input": {"command": "echo fixture"},
            }
        )
        assert_entity_identity(self, tool, "tool_call")
        approval = map_hook(
            {
                **common,
                "hook_event_name": "PermissionRequest",
                "tool_use_id": "tool_fixture_001",
                "tool_name": "Bash",
                "tool_input": {"command": "echo fixture"},
            }
        )
        assert_entity_identity(self, approval, "approval")
        prompt = map_hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "fixture"})
        assert_entity_identity(self, prompt, "node")
        self.assertEqual(prompt["type"], "galaxy.analysis.node.created.v1")
        self.assertEqual(prompt["data"]["node"]["node_type"], "analysis")
        agent = map_hook(
            {
                **common,
                "hook_event_name": "SubagentStart",
                "agent_id": "agent_fixture_001",
                "agent_type": "worker",
            }
        )
        assert_entity_identity(self, agent, "agent")

    def test_spool_deduplicates_and_capture_is_fail_open(self) -> None:
        event = map_hook(fixture("codex_hook_session_start.json"))
        with tempfile.TemporaryDirectory() as directory:
            first = spool_event(event, directory)
            second = spool_event(event, directory)
            self.assertEqual(first, second)
            self.assertEqual(len(list(Path(directory).glob("evt_*.json"))), 1)
            old_stdin = sys.stdin
            try:
                sys.stdin = io.StringIO("not-json")
                self.assertEqual(capture_stdin(spool=directory), 0)
                sys.stdin = io.StringIO(
                    "\ufeff" + json.dumps(fixture("codex_hook_session_start.json"))
                )
                self.assertEqual(capture_stdin(spool=directory), 0)
                pending = sorted(
                    Path(directory).glob("evt_*.json"),
                    key=lambda path: (path.stat().st_mtime_ns, path.name),
                )
                self.assertEqual(len(pending), 2)
                self.assertEqual(
                    [json.loads(path.read_text(encoding="utf-8"))["type"] for path in pending],
                    ["galaxy.analysis.run.created.v1", "galaxy.analysis.run.started.v1"],
                )
                sys.stdin = io.StringIO(
                    "\u00ef\u00bb\u00bf" + json.dumps(fixture("codex_hook_session_start.json"))
                )
                self.assertEqual(capture_stdin(spool=directory), 0)
            finally:
                sys.stdin = old_stdin

    def test_app_server_notification_and_sdk_result(self) -> None:
        event = map_notification(fixture("codex_app_server_turn_started.json"))
        self.assertEqual(event["type"], "galaxy.analysis.run.started.v1")
        assert_entity_identity(self, event, "run")
        with self.assertRaises(ValueError):
            map_notification({"id": 1, "result": {}})
        sdk_fixture = fixture("codex_sdk_result.json")
        result = map_run_result(
            thread_id=sdk_fixture["thread_id"],
            final_response=sdk_fixture["final_response"],
        )
        run_entity = assert_entity_identity(self, result, "run")
        self.assertTrue(run_entity["final_response"]["redacted"])
        with self.assertRaises(ValueError):
            map_run_result(thread_id="", final_response="fixture")

    def test_flusher_acknowledges_successful_delivery(self) -> None:
        received: list[dict] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                size = int(self.headers["Content-Length"])
                received.append(json.loads(self.rfile.read(size)))
                self.send_response(202)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                spool_event(map_hook(fixture("codex_hook_session_start.json")), directory)
                sent, failed = flush_once(
                    spool=directory,
                    endpoint=f"http://127.0.0.1:{server.server_port}/api/v1/events",
                )
                self.assertEqual((sent, failed), (1, 0))
                self.assertEqual(len(received), 1)
                self.assertEqual(list(Path(directory).glob("evt_*.json")), [])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


class JsonlTests(unittest.TestCase):
    def test_writer_and_resumable_tailer_ignore_partial_line(self) -> None:
        run_id = "run_123456789abc4def8abc123456789abc"
        event = build_event(
            event_type="galaxy.telemetry.metric.recorded.v1",
            source="urn:test",
            subject=run_id,
            run_id=run_id,
            data={"value": 1},
            adapter="test/1",
            native_id="metric-1",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            JsonlWriter(path).write(event)
            with path.open("ab") as handle:
                handle.write(b'{"partial":true}')
            tailer = JsonlTailer(path)
            records = list(tailer.poll())
            self.assertEqual(len(records), 1)
            saved_offset = tailer.offset
            self.assertEqual(list(tailer.poll()), [])
            self.assertEqual(tailer.offset, saved_offset)


class StandardsAdapterTests(unittest.TestCase):
    def test_ag_ui_supported_and_unknown_events(self) -> None:
        started = map_ag_ui(fixture("ag_ui_run_started.json"))
        self.assertEqual(started["type"], "galaxy.analysis.run.started.v1")
        assert_entity_identity(self, started, "run")
        self.assertEqual(started["data"]["native"]["input"], "[REDACTED_CONTENT]")
        unknown = map_ag_ui({"type": "VENDOR_EVENT", "runId": "run-1", "vendor": {"x": 1}})
        self.assertEqual(unknown["type"], "galaxy.integration.ag_ui_event.received.v1")
        self.assertEqual(unknown["data"]["native"]["vendor"], {"x": 1})

    def test_a2a_task_mapping(self) -> None:
        event = map_task({"id": "task-1", "contextId": "ctx-1", "status": {"state": "working"}})
        self.assertEqual(event["type"], "galaxy.analysis.node.started.v1")
        assert_entity_identity(self, event, "node")
        with self.assertRaises(ValueError):
            map_task({"status": {"state": "working"}})
        with self.assertRaises(ValueError):
            map_agent_card({})
        card = map_agent_card({"name": "Fixture agent"})
        self.assertEqual(card["type"], "galaxy.integration.a2a_agent.discovered.v1")

    def test_openlineage_round_trip_subset(self) -> None:
        native = fixture("openlineage_run_event.json")
        events = ingest_run_event(native)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["type"], "galaxy.analysis.run.started.v1")
        assert_entity_identity(self, events[0], "run")
        assert_entity_identity(self, events[1], "dataset")
        assert_entity_identity(self, events[2], "dataset")
        exported = export_run_event(
            events,
            producer="https://example.invalid/asterism/0.1",
            schema_url=native["schemaURL"],
            job_namespace="example.analytics",
            job_name="customer_churn",
            native_run_id=native["run"]["runId"],
        )
        self.assertEqual(exported["eventType"], "START")
        self.assertEqual(exported["inputs"][0]["name"], "customers")
        self.assertEqual(exported["outputs"][0]["name"], "churn_features")

    def test_otlp_json_narrow_mapping(self) -> None:
        traces = list(map_traces_json(fixture("otlp_traces.json")))
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["type"], "galaxy.telemetry.span.recorded.v1")
        logs = list(
            map_logs_json(
                {
                    "resourceLogs": [
                        {"scopeLogs": [{"logRecords": [{"body": {"stringValue": "hidden"}}]}]}
                    ]
                }
            )
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["data"]["otlp"]["body"], "[REDACTED_CONTENT]")
        with self.assertRaises(UnsupportedOtlpPayload):
            list(map_traces_json({"notOtlp": []}))


class FakeSpanData:
    type = "function"

    def export(self) -> dict:
        return {
            "type": "function",
            "name": "lookup",
            "input": "secret argument",
            "output": "secret result",
        }


class FakeSpan:
    trace_id = "trace-1"
    span_id = "span-1"
    parent_id = None
    started_at = "2026-07-17T10:00:00Z"
    ended_at = "2026-07-17T10:00:01Z"
    error = None
    span_data = FakeSpanData()


class FakeTrace:
    trace_id = "trace-1"
    name = "fixture trace"
    group_id = "group-1"


class AgentAndSdkTests(unittest.TestCase):
    def test_agents_processor_public_callbacks_and_redaction(self) -> None:
        exported = fixture("openai_agents_function_span.json")
        sdk_span = FakeSpan()
        sdk_span.trace_id = exported["trace_id"]
        sdk_span.span_id = exported["id"]
        sdk_span.parent_id = exported["parent_id"]
        sdk_span.started_at = exported["started_at"]
        sdk_span.ended_at = exported["ended_at"]
        sdk_span.error = exported["error"]
        sdk_span.span_data = FakeSpanData()
        sdk_span.span_data.export = lambda: exported["span_data"]
        events: list[dict] = []
        processor = AsterismTracingProcessor(events.append)
        processor.on_trace_start(FakeTrace())
        processor.on_span_start(sdk_span)
        processor.on_span_end(sdk_span)
        processor.on_trace_end(FakeTrace())
        self.assertEqual(len(events), 4)
        self.assertEqual(events[1]["type"], "galaxy.analysis.toolcall.started.v1")
        assert_entity_identity(self, events[0], "run")
        assert_entity_identity(self, events[1], "tool_call")
        assert_entity_identity(self, events[2], "tool_call")
        assert_entity_identity(self, events[3], "run")
        self.assertTrue(events[1]["data"]["span_data"]["input"]["redacted"])
        repeated = processor._span_event(sdk_span, "start")
        self.assertNotEqual(events[1]["id"], repeated["id"])
        self.assertEqual(
            events[1]["data"]["integration"]["deduplication_key"],
            repeated["data"]["integration"]["deduplication_key"],
        )

    def test_python_sdk_contexts_decorator_and_artifact(self) -> None:
        sink = ListSink()
        client = GalaxyClient(sink)
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "chart.json"
            artifact_path.write_text("{}", encoding="utf-8")
            with client.start_run(title="Investigation", objective="Test") as run:

                @run.instrument_node(title="Decorated", node_type="validation")
                def decorated() -> int:
                    return 7

                self.assertEqual(decorated(), 7)
                with run.start_node(title="Explore", node_type="exploration") as node:
                    with node.start_tool_call("python") as call:
                        artifact = call.register_artifact(
                            path=artifact_path, artifact_type="chart", title="Chart"
                        )
                    node.create_claim(
                        title="Claim", statement="Fixture", evidence_artifact_ids=[artifact.id]
                    )
            with self.assertRaises(RuntimeError):
                with client.start_run(title="Failure", objective="Test failure identity"):
                    raise RuntimeError("fixture failure")
        event_types = [event["type"] for event in sink.events]
        self.assertIn("galaxy.analysis.artifact.created.v1", event_types)
        self.assertIn("galaxy.analysis.claim.created.v1", event_types)
        self.assertTrue(all("sequence" not in event for event in sink.events))
        artifact_event = next(
            event for event in sink.events if event["type"] == "galaxy.analysis.artifact.created.v1"
        )
        self.assertNotIn(str(artifact_path), json.dumps(artifact_event))
        self.assertIn("/artifact/art_", artifact_event["subject"])
        semantic_keys = {
            "run": "run",
            "node": "node",
            "toolcall": "tool_call",
            "artifact": "artifact",
            "claim": "claim",
        }
        for event in sink.events:
            parts = event["type"].split(".")
            if parts[1] == "analysis" and parts[2] in semantic_keys:
                assert_entity_identity(self, event, semantic_keys[parts[2]])
        completed = [
            event for event in sink.events if event["type"].endswith(("completed.v1", "failed.v1"))
        ]
        self.assertGreaterEqual(len(completed), 4)
        for event in completed:
            parts = event["type"].split(".")
            if parts[1] == "analysis":
                assert_entity_identity(self, event, semantic_keys[parts[2]])
        failed_run = next(
            event for event in sink.events if event["type"] == "galaxy.analysis.run.failed.v1"
        )
        failed_entity = assert_entity_identity(self, failed_run, "run")
        self.assertEqual(failed_entity["status"], "failed")


class FixtureTests(unittest.TestCase):
    def test_all_json_fixtures_and_hook_config_parse(self) -> None:
        for path in FIXTURES.glob("*.json"):
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)
        hooks = json.loads(
            (ROOT / "examples" / "integrations" / "codex" / "hooks.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("SessionStart", hooks["hooks"])
        typescript = (ROOT / "sdk" / "typescript" / "src" / "index.ts").read_text(encoding="utf-8")
        self.assertIn('"analysis.toolcall": "tool_call"', typescript)
        self.assertIn("requires data.${key} with id, run_id, and schema_version", typescript)


if __name__ == "__main__":
    unittest.main()
