from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "events"
EXAMPLE_DIR = ROOT / "schemas" / "examples"

CASES = (
    ("run-created.v1.schema.json", "run-created.v1.json"),
    ("node-created.v1.schema.json", "node-created.v1.json"),
    ("artifact-created.v1.schema.json", "artifact-created.v1.json"),
)
SCHEMAS = tuple(sorted(path.name for path in SCHEMA_DIR.glob("*.json")))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_registry() -> Registry[Any]:
    registry: Registry[Any] = Registry()
    for path in SCHEMA_DIR.glob("*.json"):
        contents = load_json(path)
        registry = registry.with_resource(contents["$id"], Resource.from_contents(contents))
    return registry


def validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        load_json(SCHEMA_DIR / schema_name),
        registry=schema_registry(),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_json_schema_is_valid(schema_name: str) -> None:
    Draft202012Validator.check_schema(load_json(SCHEMA_DIR / schema_name))


@pytest.mark.parametrize(("schema_name", "example_name"), CASES)
def test_representative_event_matches_schema(schema_name: str, example_name: str) -> None:
    validator(schema_name).validate(load_json(EXAMPLE_DIR / example_name))


def test_persisted_event_requires_allocated_sequence() -> None:
    event = load_json(EXAMPLE_DIR / "run-created.v1.json")
    event.pop("sequence")

    with pytest.raises(ValidationError):
        validator("run-created.v1.schema.json").validate(event)


def test_envelope_rejects_unknown_top_level_fields() -> None:
    event = copy.deepcopy(load_json(EXAMPLE_DIR / "artifact-created.v1.json"))
    event["camera_position"] = {"x": 10, "y": 20}

    with pytest.raises(ValidationError):
        validator("artifact-created.v1.schema.json").validate(event)


def test_trace_context_cannot_use_all_zero_identifiers() -> None:
    event = copy.deepcopy(load_json(EXAMPLE_DIR / "node-created.v1.json"))
    event["traceid"] = "0" * 32

    with pytest.raises(ValidationError):
        validator("node-created.v1.schema.json").validate(event)


def test_generic_semantic_schema_accepts_registered_event() -> None:
    event = load_json(EXAMPLE_DIR / "run-created.v1.json")

    validator("semantic-event-v1.json").validate(event)
