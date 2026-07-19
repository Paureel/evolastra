from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.harness import PUBLIC_SHOWCASE_PATH, check_public_showcase_boundary

ROOT = Path(__file__).resolve().parents[1]


def test_public_showcase_is_the_only_hosted_analysis_and_is_aggregate_only() -> None:
    assert check_public_showcase_boundary(ROOT) == []
    showcase = json.loads((ROOT / PUBLIC_SHOWCASE_PATH).read_text(encoding="utf-8"))

    assert showcase["public"] is True
    assert showcase["run"]["privacy_class"] == "public"
    assert showcase["state"]["last_sequence"] == 12
    assert showcase["replay"]["last_sequence"] == 12
    assert [phase["sequence"] for phase in showcase["replay"]["phases"]] == list(range(1, 13))
    assert len(showcase["multiplayer"]["players"]) == 3
    assert len(showcase["multiplayer"]["claims"]) == 10
    assert Counter(claim["player_id"] for claim in showcase["multiplayer"]["claims"]) == {
        "demo_player_gold": 4,
        "demo_player_cyan": 3,
        "demo_player_purple": 3,
    }
    assert len(showcase["multiplayer"]["publications"]) == 6
    assert len(showcase["state"]["artifacts"]) == 6
    assert all(len(artifact["preview"]["values"]) <= 12 for artifact in showcase["state"]["artifacts"])


def test_public_showcase_preserves_the_six_semantic_research_directions() -> None:
    showcase = json.loads((ROOT / PUBLIC_SHOWCASE_PATH).read_text(encoding="utf-8"))
    hypotheses = [
        node for node in showcase["state"]["nodes"]
        if node.get("node_type") == "hypothesis"
    ]

    assert len(hypotheses) == 6
    assert {node["semantic_signature"]["program"] for node in hypotheses} == {
        "amplification-dependency",
        "deletion-vulnerability",
        "co-alteration-combination",
    }
    claimed = {claim["node_id"] for claim in showcase["multiplayer"]["claims"]}
    assert {node["id"] for node in hypotheses} <= claimed
    assert {
        "demo_node_amplified_drivers",
        "demo_node_suppressor_losses",
        "demo_node_coalterations",
    } <= claimed
