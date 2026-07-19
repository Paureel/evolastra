from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "simulate_stad_multiplayer", ROOT / "scripts" / "simulate_stad_multiplayer.py"
)
assert SPEC and SPEC.loader
simulation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(simulation)


def test_three_empire_spec_is_fixed_distinct_and_falsifiable() -> None:
    empires = simulation.EMPIRES
    systems = [system for empire in empires for system in empire["systems"]]
    assert len(empires) == 3
    assert len(systems) == 6
    assert len({empire["name"] for empire in empires}) == 3
    assert len({empire["color"] for empire in empires}) == 3
    assert len({system["node_id"] for system in systems}) == 6
    assert all(system["prediction"] and system["falsifier"] and system["required_validation"] for system in systems)
    assert {empire["program"] for empire in empires} == {
        "amplification-dependency",
        "deletion-vulnerability",
        "co-alteration-combination",
    }


def test_summary_validation_is_bounded_to_the_recorded_stad_aggregate() -> None:
    valid = {
        "sample_count": 438,
        "gene_count": 25_128,
        "top_amplifications": [{}] * 10,
        "top_losses": [{}] * 10,
    }
    simulation.validate_summary(valid)
    with pytest.raises(RuntimeError, match="438 tumors"):
        simulation.validate_summary({**valid, "sample_count": 437})
