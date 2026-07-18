from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .database import SessionLocal
from .event_store import EventStore, make_event
from .schemas import CloudEvent, RunCreate

DEMO_SEED = 20260717
logger = logging.getLogger(__name__)


@dataclass
class SimulatorControl:
    speed: float = 6.0
    stopped: bool = False


controls: dict[str, SimulatorControl] = {}
tasks: dict[str, threading.Thread] = {}


BRANCHES = [
    ("Data ingress", "data", "Inspect source tables and establish quality baselines"),
    ("Tenure signal", "exploration", "Test whether early-tenure churn is concentrated"),
    ("Contract friction", "exploration", "Measure contract and billing associations"),
    ("Support burden", "exploration", "Relate support interactions to churn outcomes"),
    ("Model comparison", "modeling", "Compare calibrated predictive models"),
    ("Robustness checks", "validation", "Challenge high-impact associations"),
    ("Reproduction", "validation", "Reproduce promoted findings from pinned inputs"),
    ("Evidence synthesis", "synthesis", "Reconcile contradictions and produce the report"),
]


def _trace(rng: random.Random) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(32))


def _span(rng: random.Random) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(16))


def _event(
    run_id: str,
    event_type: str,
    subject: str,
    data: dict[str, Any],
    rng: random.Random,
    *,
    causation: str | None = None,
) -> CloudEvent:
    return make_event(
        run_id=run_id,
        event_type=event_type,
        subject=subject,
        data=data,
        trace_id=_trace(rng),
        span_id=_span(rng),
        causation_id=causation,
        event_id=_seeded_id("evt", rng),
        event_time=datetime(2026, 7, 17, 14, 20, 30, 123000, tzinfo=UTC),
    )


def _seeded_id(prefix: str, rng: random.Random) -> str:
    return f"{prefix}_{uuid.UUID(int=rng.getrandbits(128), version=4).hex}"


def build_demo_events(run_id: str, seed: int = DEMO_SEED) -> list[CloudEvent]:
    rng = random.Random(f"{seed}:{run_id}")  # noqa: S311 - deterministic fixture only
    events: list[CloudEvent] = []
    root_id = _seeded_id("node", rng)
    lead_agent = _seeded_id("agent", rng)
    now = datetime(2026, 7, 17, 14, 20, 30, 123000, tzinfo=UTC).isoformat()

    events.append(
        _event(
            run_id,
            "galaxy.analysis.run.started.v1",
            f"run/{run_id}",
            {"run": {"id": run_id, "status": "running", "start_time": now}},
            rng,
        )
    )
    root = {
        "id": root_id,
        "run_id": run_id,
        "parent_node_id": None,
        "node_type": "objective",
        "title": "Explain customer churn without overstating evidence",
        "description": "A seeded, fully replayable investigation of churn drivers and limitations.",
        "explicit_objective": "Identify reliable drivers of customer churn",
        "status": "running",
        "priority": "critical",
        "phase": "framing",
        "topic": "customer churn",
        "assigned_agent_ids": [lead_agent],
        "creation_source": "simulator",
        "promotion_reason": "root objective",
        "progress": 0.05,
        "tags": ["demo", "churn", "reproducible"],
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.node.created.v1",
            f"run/{run_id}/node/{root_id}",
            {"node": root},
            rng,
        )
    )
    agent = {
        "id": lead_agent,
        "run_id": run_id,
        "parent_agent_id": None,
        "name": "Kepler",
        "role": "analysis lead",
        "model": "simulated",
        "provider": "local",
        "framework": "asterism-simulator",
        "status": "running",
        "current_node_id": root_id,
        "capabilities": ["delegation", "synthesis", "validation"],
        "permissions_profile": "demo-readonly",
        "tool_access_profile": ["python", "sql", "chart"],
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.agent.created.v1",
            f"run/{run_id}/agent/{lead_agent}",
            {"agent": agent},
            rng,
        )
    )
    events.append(
        _event(
            run_id,
            "galaxy.analysis.agent.started.v1",
            f"run/{run_id}/agent/{lead_agent}",
            {"agent": agent},
            rng,
        )
    )

    dataset_id = _seeded_id("data", rng)
    version_id = _seeded_id("dver", rng)
    dataset = {
        "id": dataset_id,
        "run_id": run_id,
        "name": "Northstar telecom retention cohort",
        "namespace": "demo://customer-success",
        "description": "Synthetic customer-level cohort with contract, tenure, billing, and support fields.",
        "format": "parquet",
        "size_bytes": 2_840_192,
        "row_count": 7_043,
        "column_count": 21,
        "privacy_classification": "internal",
        "node_id": root_id,
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.dataset.registered.v1",
            f"run/{run_id}/dataset/{dataset_id}",
            {"dataset": dataset},
            rng,
        )
    )
    version = {
        "id": version_id,
        "dataset_id": dataset_id,
        "run_id": run_id,
        "version": "sha256:ee5e5e0c-demo",
        "schema": [
            {"name": "tenure_months", "type": "integer", "null_count": 0},
            {"name": "monthly_charges", "type": "number", "null_count": 0},
            {"name": "contract", "type": "string", "null_count": 0},
            {"name": "churn", "type": "boolean", "null_count": 0},
        ],
        "statistics": {"rows": 7043, "sampled": False, "null_cells": 11},
        "parent_id": dataset_id,
        "node_id": root_id,
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.dataset_version.created.v1",
            f"run/{run_id}/dataset-version/{version_id}",
            {"dataset_version": version},
            rng,
        )
    )

    branch_nodes: list[str] = []
    branch_agents: list[str] = []
    all_artifacts: list[str] = []
    claims: list[str] = []
    findings: list[str] = []
    for index, (title, node_type, objective) in enumerate(BRANCHES):
        node_id = _seeded_id("node", rng)
        agent_id = _seeded_id("agent", rng)
        branch_nodes.append(node_id)
        branch_agents.append(agent_id)
        node = {
            "id": node_id,
            "run_id": run_id,
            "parent_node_id": root_id,
            "node_type": node_type,
            "title": title,
            "description": objective,
            "explicit_objective": objective,
            "status": "created",
            "priority": "high" if index in {0, 5, 6, 7} else "normal",
            "phase": "analysis" if index < 5 else "validation",
            "topic": title.lower(),
            "assigned_agent_ids": [agent_id],
            "creation_source": "delegation",
            "promotion_reason": "distinct delegated analytical objective",
            "progress": 0,
            "tags": [node_type, "demo"],
        }
        events.append(
            _event(
                run_id,
                "galaxy.analysis.node.created.v1",
                f"run/{run_id}/node/{node_id}",
                {"node": node},
                rng,
            )
        )
        subagent = {
            "id": agent_id,
            "run_id": run_id,
            "parent_agent_id": lead_agent,
            "name": ["Lyra", "Vela", "Mira", "Altair", "Corvus", "Cygnus", "Sagan", "Vega"][index],
            "role": f"{title.lower()} specialist",
            "model": "simulated",
            "provider": "local",
            "framework": "asterism-simulator",
            "status": "created",
            "current_node_id": node_id,
            "capabilities": [node_type, "evidence"],
            "permissions_profile": "demo-readonly",
            "tool_access_profile": ["python", "sql"] if index < 6 else ["python", "report"],
        }
        events.append(
            _event(
                run_id,
                "galaxy.analysis.agent.created.v1",
                f"run/{run_id}/agent/{agent_id}",
                {"agent": subagent},
                rng,
            )
        )
        events.append(
            _event(
                run_id,
                "galaxy.analysis.agent.started.v1",
                f"run/{run_id}/agent/{agent_id}",
                {"agent": {**subagent, "status": "running"}},
                rng,
            )
        )
        events.append(
            _event(
                run_id,
                "galaxy.analysis.node.started.v1",
                f"run/{run_id}/node/{node_id}",
                {"node": {**node, "status": "running", "progress": 0.1}},
                rng,
            )
        )

        for tool_index in range(4):
            tool_id = _seeded_id("tool", rng)
            tool = {
                "id": tool_id,
                "run_id": run_id,
                "node_id": node_id,
                "agent_id": agent_id,
                "tool_name": ["duckdb", "python", "quality-check", "vega-lite"][tool_index],
                "tool_category": ["query", "compute", "validation", "visualization"][tool_index],
                "status": "requested",
                "attempt": 1,
                "input_summary": f"Bounded demo operation {tool_index + 1}",
                "output_summary": "",
                "trace_id": _trace(rng),
                "span_id": _span(rng),
                "token_metrics": {"input": 70 + index * 3, "output": 30 + tool_index * 5},
                "timing_metrics": {"duration_ms": 210 + index * 37 + tool_index * 45},
                "cost_metrics": {"currency": "USD", "total": round(0.0007 + index * 0.0001, 5)},
            }
            events.append(
                _event(
                    run_id,
                    "galaxy.analysis.tool_call.requested.v1",
                    f"run/{run_id}/tool/{tool_id}",
                    {"tool_call": tool},
                    rng,
                )
            )
            events.append(
                _event(
                    run_id,
                    "galaxy.analysis.tool_call.started.v1",
                    f"run/{run_id}/tool/{tool_id}",
                    {"tool_call": {**tool, "status": "running"}},
                    rng,
                )
            )
            if index == 2 and tool_index == 1:
                events.append(
                    _event(
                        run_id,
                        "galaxy.analysis.tool_call.failed.v1",
                        f"run/{run_id}/tool/{tool_id}",
                        {
                            "tool_call": {
                                **tool,
                                "status": "failed",
                                "error": "Synthetic numerical convergence failure",
                                "retry_count": 1,
                            }
                        },
                        rng,
                    )
                )
                recovery_id = _seeded_id("tool", rng)
                events.append(
                    _event(
                        run_id,
                        "galaxy.analysis.tool_call.completed.v1",
                        f"run/{run_id}/tool/{recovery_id}",
                        {
                            "tool_call": {
                                **tool,
                                "id": recovery_id,
                                "status": "completed",
                                "attempt": 2,
                                "output_summary": "Recovered with a robust solver",
                            }
                        },
                        rng,
                    )
                )
            else:
                events.append(
                    _event(
                        run_id,
                        "galaxy.analysis.tool_call.completed.v1",
                        f"run/{run_id}/tool/{tool_id}",
                        {
                            "tool_call": {
                                **tool,
                                "status": "completed",
                                "output_summary": "Operation completed on bounded synthetic data",
                            }
                        },
                        rng,
                    )
                )

        artifact_id = _seeded_id("art", rng)
        all_artifacts.append(artifact_id)
        values = [
            {"label": "0–6 mo", "value": 0.47 - index * 0.015},
            {"label": "7–18 mo", "value": 0.27 + index * 0.005},
            {"label": "19–36 mo", "value": 0.17},
            {"label": "37+ mo", "value": 0.09 + index * 0.01},
        ]
        artifact = {
            "id": artifact_id,
            "run_id": run_id,
            "node_id": node_id,
            "dataset_version_id": version_id,
            "artifact_type": "vega_lite" if index % 2 == 0 else "table",
            "title": f"{title} evidence view",
            "description": f"Portable evidence artifact for {objective.lower()}.",
            "mime_type": "application/vnd.vegalite.v5+json"
            if index % 2 == 0
            else "application/json",
            "size_bytes": 1400 + index * 122,
            "hash": f"sha256:demo{index:02d}",
            "preview_status": "ready",
            "provenance": {
                "dataset_version_id": version_id,
                "agent_id": agent_id,
                "tool": "vega-lite",
            },
            "preview": {"kind": "bar", "values": values, "sampled": False, "row_count": 4},
            "created_time": now,
        }
        events.append(
            _event(
                run_id,
                "galaxy.analysis.artifact.created.v1",
                f"run/{run_id}/artifact/{artifact_id}",
                {"artifact": artifact},
                rng,
            )
        )

        claim_id = _seeded_id("claim", rng)
        claims.append(claim_id)
        disputed = index in {2, 4}
        claim = {
            "id": claim_id,
            "run_id": run_id,
            "node_id": node_id,
            "title": f"{title} association",
            "statement": [
                "Churn is concentrated in the first six months.",
                "Tenure remains associated with churn after stratification.",
                "Month-to-month contracts appear to increase churn.",
                "Repeated support contacts are associated with higher churn.",
                "The calibrated gradient model outperforms the linear baseline.",
                "The tenure association is robust to alternative binning.",
                "Seven of eight promoted findings reproduce from pinned inputs.",
                "The combined evidence supports targeted onboarding, not causal claims.",
            ][index],
            "claim_type": "association" if index != 6 else "reproduction",
            "validation_status": "disputed" if disputed else "validated",
            "confidence_type": "reported",
            "confidence": round(0.72 + index * 0.025, 2),
            "statistical_metadata": {
                "effect": round(0.31 - index * 0.018, 3),
                "p_value": round(0.004 + index * 0.006, 3),
            },
            "importance": "major" if index in {0, 5, 7} else "normal",
            "artifact_ids": [artifact_id],
            "assumptions": ["synthetic cohort", "observational association"],
        }
        events.append(
            _event(
                run_id,
                "galaxy.analysis.claim.created.v1",
                f"run/{run_id}/claim/{claim_id}",
                {"claim": claim},
                rng,
            )
        )
        validation_type = "disputed" if disputed else "validated"
        events.append(
            _event(
                run_id,
                f"galaxy.analysis.claim.{validation_type}.v1",
                f"run/{run_id}/claim/{claim_id}",
                {"claim": claim},
                rng,
            )
        )
        evidence_id = _seeded_id("evid", rng)
        evidence = {
            "id": evidence_id,
            "run_id": run_id,
            "claim_id": claim_id,
            "artifact_id": artifact_id,
            "node_id": node_id,
            "relationship": "contradicts" if disputed else "supports",
            "strength": round(0.65 + index * 0.03, 2),
            "description": "Bounded, traceable simulator evidence",
        }
        events.append(
            _event(
                run_id,
                "galaxy.analysis.evidence.attached.v1",
                f"run/{run_id}/evidence/{evidence_id}",
                {"evidence": evidence},
                rng,
            )
        )

        finding_id = _seeded_id("find", rng)
        findings.append(finding_id)
        finding = {
            "id": finding_id,
            "run_id": run_id,
            "node_id": node_id,
            "title": f"Finding: {title}",
            "summary": claim["statement"],
            "claim_ids": [claim_id],
            "evidence_ids": [evidence_id],
            "artifact_ids": [artifact_id],
            "validation_status": claim["validation_status"],
            "importance": "major",
            "reproducible": index != 6,
        }
        events.append(
            _event(
                run_id,
                "galaxy.analysis.finding.created.v1",
                f"run/{run_id}/finding/{finding_id}",
                {"finding": finding},
                rng,
            )
        )
        events.append(
            _event(
                run_id,
                "galaxy.analysis.finding.promoted.v1",
                f"run/{run_id}/finding/{finding_id}",
                {"finding": finding},
                rng,
            )
        )
        events.append(
            _event(
                run_id,
                "galaxy.analysis.node.completed.v1",
                f"run/{run_id}/node/{node_id}",
                {"node": {**node, "status": "completed", "progress": 1}},
                rng,
            )
        )
        events.append(
            _event(
                run_id,
                "galaxy.analysis.agent.completed.v1",
                f"run/{run_id}/agent/{agent_id}",
                {"agent": {**subagent, "status": "completed"}},
                rng,
            )
        )

    for title, objective in (
        ("Pricing sensitivity", "Explore whether targeted pricing tests alter retention"),
        ("Onboarding sequence", "Test which early onboarding interactions precede retention"),
    ):
        unexplored_id = _seeded_id("node", rng)
        unexplored = {
            "id": unexplored_id,
            "run_id": run_id,
            "parent_node_id": root_id,
            "node_type": "unexplored",
            "title": title,
            "description": objective,
            "explicit_objective": objective,
            "status": "unexplored",
            "priority": "normal",
            "phase": "future",
            "topic": title.lower(),
            "assigned_agent_ids": [],
            "creation_source": "synthesis",
            "promotion_reason": "retained as an explicit unexplored direction",
            "progress": 0,
            "tags": ["unexplored", "follow-up"],
        }
        events.append(
            _event(
                run_id,
                "galaxy.analysis.node.proposed.v1",
                f"run/{run_id}/node/{unexplored_id}",
                {"node": unexplored},
                rng,
            )
        )

    anomaly_id = _seeded_id("anom", rng)
    anomaly = {
        "id": anomaly_id,
        "run_id": run_id,
        "node_id": branch_nodes[5],
        "title": "Unexpected senior-cohort reversal",
        "description": "A small subgroup reverses the aggregate billing association.",
        "severity": "warning",
        "status": "open",
        "resolution": None,
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.anomaly.created.v1",
            f"run/{run_id}/anomaly/{anomaly_id}",
            {"anomaly": anomaly},
            rng,
        )
    )

    reproduction_anomaly_id = _seeded_id("anom", rng)
    reproduction_anomaly = {
        "id": reproduction_anomaly_id,
        "run_id": run_id,
        "node_id": branch_nodes[6],
        "anomaly_type": "failed_reproduction",
        "title": "Reproduction checksum mismatch",
        "description": "One model-comparison artifact did not match its pinned environment digest.",
        "severity": "error",
        "status": "failed",
        "resolution": None,
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.anomaly.created.v1",
            f"run/{run_id}/anomaly/{reproduction_anomaly_id}",
            {"anomaly": reproduction_anomaly},
            rng,
        )
    )
    events.append(
        _event(
            run_id,
            "galaxy.analysis.anomaly.resolved.v1",
            f"run/{run_id}/anomaly/{anomaly_id}",
            {
                "anomaly": {
                    **anomaly,
                    "status": "resolved",
                    "resolution": "Sparse subgroup; finding narrowed and caveat added.",
                }
            },
            rng,
        )
    )

    approval_id = _seeded_id("approval", rng)
    approval = {
        "id": approval_id,
        "run_id": run_id,
        "node_id": branch_nodes[7],
        "title": "Publish final synthesis",
        "requested_action": "promote report and knowledge exports",
        "risk_level": "medium",
        "status": "pending",
        "requested_by": lead_agent,
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.approval.requested.v1",
            f"run/{run_id}/approval/{approval_id}",
            {"approval": approval},
            rng,
        )
    )

    handoff = {
        **{
            "id": lead_agent,
            "run_id": run_id,
            "name": "Kepler",
            "role": "analysis lead",
            "status": "running",
            "current_node_id": branch_nodes[7],
        },
        "from_agent_id": branch_agents[5],
        "to_agent_id": lead_agent,
        "handoff_reason": "robustness review complete",
    }
    events.append(
        _event(
            run_id,
            "galaxy.analysis.agent.handed_off.v1",
            f"run/{run_id}/agent/{lead_agent}",
            {"agent": handoff},
            rng,
        )
    )
    for step in range(6):
        events.append(
            _event(
                run_id,
                "galaxy.analysis.metric.recorded.v1",
                f"run/{run_id}/metric/{step}",
                {
                    "metric": {
                        "id": _seeded_id("metr", rng),
                        "run_id": run_id,
                        "name": "tokens.total",
                        "value": 2_400 + step * 1_725,
                        "unit": "tokens",
                        "dimensions": {"phase": "analysis" if step < 4 else "synthesis"},
                        "cost_usd": round(0.041 + step * 0.017, 3),
                    }
                },
                rng,
            )
        )

    events.append(
        _event(
            run_id,
            "galaxy.analysis.node.progress.v1",
            f"run/{run_id}/node/{root_id}",
            {"node": {**root, "progress": 0.94}, "progress": 0.94},
            rng,
        )
    )
    # Completion remains gated until a human records the approval in the UI.
    return events


def run_simulation(run_id: str, events: list[CloudEvent]) -> None:
    control = controls.setdefault(run_id, SimulatorControl())
    try:
        for event in events:
            if control.stopped:
                break
            with SessionLocal() as session:
                result = EventStore(session).ingest(event.model_dump(mode="json"))
                if not result.accepted:
                    raise RuntimeError(result.reason or f"event {event.id} was rejected")
            time.sleep(max(0.015, 0.55 / max(0.1, control.speed)))
    except Exception:
        logger.exception("Demo simulator failed for run %s", run_id)
    finally:
        tasks.pop(run_id, None)


def start_demo(speed: float = 6.0) -> dict[str, Any]:
    with SessionLocal() as session:
        record, _ = EventStore(session).create_run(
            RunCreate(
                title="Churn atlas: reliable signals and caveats",
                objective="Identify reliable drivers of customer churn without overstating causal evidence",
                seed=DEMO_SEED,
                tags=["seeded-demo", "churn", "observability"],
            )
        )
        events = build_demo_events(record.id, record.seed)
    controls[record.id] = SimulatorControl(speed=max(0.1, min(speed, 50.0)))
    worker = threading.Thread(
        target=run_simulation,
        args=(record.id, events),
        daemon=True,
        name=f"evolastra-demo-{record.id[-8:]}",
    )
    tasks[record.id] = worker
    worker.start()
    return {"run_id": record.id, "seed": record.seed, "event_total": len(events), "speed": speed}


def set_speed(run_id: str, speed: float) -> bool:
    if run_id not in controls:
        return False
    controls[run_id].speed = max(0.1, min(speed, 50.0))
    return True
