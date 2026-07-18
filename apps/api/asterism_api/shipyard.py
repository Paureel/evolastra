from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

COMPLETE_STATUSES = {"approved", "completed", "promoted", "resolved", "validated"}


@dataclass(frozen=True)
class ShipBlueprint:
    id: str
    name: str
    hull: str
    role: str
    description: str
    capabilities: tuple[str, ...]
    source_node_id: str | None = None
    source_title: str | None = None
    source_objective: str | None = None

    def public(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = list(self.capabilities)
        payload.pop("source_objective")
        return payload


DEFAULT_BLUEPRINTS = (
    ShipBlueprint(
        id="frigate",
        name="Frigate",
        hull="frigate",
        role="Focused Codex agent",
        description="A fast generalist for one bounded implementation, diagnosis, or review mission.",
        capabilities=("focused execution", "repository work", "verification"),
    ),
    ShipBlueprint(
        id="mothership",
        name="Mothership",
        hull="mothership",
        role="Multi-agent mission commander",
        description="A command vessel that can delegate independent work to additional Codex agents.",
        capabilities=("delegation", "parallel investigation", "synthesis"),
    ),
    ShipBlueprint(
        id="colony",
        name="Colony ship",
        hull="colony",
        role="Novel-direction explorer",
        description="An exploration vessel prompted to establish a rigorous foothold in a new direction.",
        capabilities=("novelty search", "hypothesis formation", "frontier mapping"),
    ),
)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:36] or "specialist"


def _is_completed(node: dict[str, Any]) -> bool:
    return str(node.get("status", "created")) in COMPLETE_STATUSES or float(
        node.get("progress") or 0
    ) >= 1


def specialist_blueprint(node: dict[str, Any]) -> ShipBlueprint:
    title = str(node.get("title") or "Research")[:120]
    objective = str(
        node.get("explicit_objective") or node.get("description") or f"Apply {title} research"
    )[:2_000]
    node_type = str(node.get("node_type") or "analysis").replace("_", " ")
    return ShipBlueprint(
        id=f"specialist:{node['id']}",
        name=f"{title} specialist",
        hull="specialist",
        role=f"{node_type.title()} research vessel",
        description=f"Unlocked by {title}. Tuned to extend or apply that completed line of research.",
        capabilities=(node_type, title.casefold(), "problem-specific execution"),
        source_node_id=str(node["id"]),
        source_title=title,
        source_objective=objective,
    )


def blueprint_catalog(state: dict[str, Any]) -> list[ShipBlueprint]:
    nodes = state.get("nodes", [])
    if isinstance(nodes, dict):
        nodes = list(nodes.values())
    specialists = [
        specialist_blueprint(node)
        for node in nodes
        if isinstance(node, dict) and node.get("id") and node.get("parent_node_id") and _is_completed(node)
    ]
    specialists.sort(key=lambda blueprint: (blueprint.name.casefold(), blueprint.id))
    return [*DEFAULT_BLUEPRINTS, *specialists]


def find_blueprint(state: dict[str, Any], blueprint_id: str) -> ShipBlueprint | None:
    return next(
        (blueprint for blueprint in blueprint_catalog(state) if blueprint.id == blueprint_id),
        None,
    )


def ship_name(blueprint: ShipBlueprint, existing: list[dict[str, Any]]) -> str:
    ordinal = 1 + sum(
        1 for agent in existing if str(agent.get("ship_blueprint_id", "")) == blueprint.id
    )
    return f"{blueprint.name} {ordinal:02d}"


def mission_prompt(
    *,
    blueprint: ShipBlueprint,
    ship: dict[str, Any],
    run: dict[str, Any],
    user_prompt: str,
) -> str:
    directives = {
        "frigate": (
            "Execute this as one focused Codex mission. Keep scope bounded, follow repository guidance, "
            "make only justified changes, and verify the outcome."
        ),
        "mothership": (
            "Act as a mission commander. The user explicitly authorizes you to spawn Codex subagents for "
            "bounded independent subtasks when useful. Coordinate them, reconcile their results, and own "
            "the final verification."
        ),
        "colony": (
            "Treat this as exploration of a novel direction. Search for underexplored but testable paths, "
            "challenge apparent novelty, establish an evidence-backed foothold, and do not overclaim."
        ),
        "specialist": (
            f"Operate as the specialist unlocked by '{blueprint.source_title}'. Use this research mandate: "
            f"{blueprint.source_objective}. Extend or apply it specifically to the user's mission."
        ),
    }
    run_title = str(run.get("title") or "Evolastra investigation")[:300]
    run_objective = str(run.get("objective") or "Continue the active investigation")[:2_000]
    ship_label = str(ship.get("name") or blueprint.name)[:160]
    return "\n\n".join(
        [
            f"You are {ship_label}, an Evolastra {blueprint.role.lower()} launched by an explicit user action.",
            directives[blueprint.hull],
            "Work in the provided repository. Read and follow AGENTS.md and the nearest nested guidance. "
            "Use the repository's focused checks and full release gate in proportion to the mission. "
            "You may work inside the repository, but permission escalation is unavailable; report any "
            "blocked action instead of bypassing the boundary.",
            f"Parent investigation: {run_title}\nParent objective: {run_objective}",
            f"Mission from the user:\n{user_prompt.strip()}",
        ]
    )


def blueprint_slug(blueprint: ShipBlueprint) -> str:
    return _slug(blueprint.name)
