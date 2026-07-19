from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

EXPECTED_SHA256 = "75de2036e7fa12025a32176a5d7fc0639472a4371d19cf20fb7a00f098630fa2"
EXPECTED_SAMPLES = 438
EXPECTED_GENES = 25_128

EMPIRES: tuple[dict[str, Any], ...] = (
    {
        "name": "Amplification Dominion",
        "color": "#F0C75E",
        "agent_id": "agent_71111111111141118111111111111111",
        "program": "amplification-dependency",
        "systems": (
            {
                "node_id": "node_11111111111141118111111111111111",
                "finding_id": "find_71111111111141118111111111111111",
                "title": "MYC–ATR stress dependency",
                "alteration_direction": "gain",
                "genes": ["MYC"],
                "cytobands": ["8q24.21"],
                "mechanisms": ["replication-stress", "transcriptional-stress", "ATR"],
                "therapeutic_modalities": ["ATR-inhibition"],
                "validation_modalities": ["focality", "dosage", "CRISPR", "drug-response"],
                "summary": "MYC high-level gain occurred in 17.6% of tumors; test whether confirmed MYC dosage creates selective ATR/transcriptional-stress dependence.",
                "prediction": "MYC-amplified, dosage-confirmed models will be more sensitive to ATR or transcriptional-stress perturbation than matched copy-neutral models.",
                "falsifier": "No selective response remains after purity, ploidy, focality, and expression matching.",
                "required_validation": "Segment-level focality, RNA/protein dosage, then matched CRISPR and drug response.",
            },
            {
                "node_id": "node_2222222222224222a222222222222222",
                "finding_id": "find_7222222222224222a222222222222222",
                "title": "CCNE1 replication-stress dependency",
                "alteration_direction": "gain",
                "genes": ["CCNE1"],
                "cytobands": ["19q12"],
                "mechanisms": ["replication-stress", "cell-cycle", "ATR"],
                "therapeutic_modalities": ["CDK2-inhibition", "PKMYT1-inhibition"],
                "validation_modalities": ["focality", "dosage", "CRISPR", "drug-response"],
                "summary": "CCNE1 high-level gain occurred in 13.0% of tumors; test selective CDK2/PKMYT1 vulnerability after dosage confirmation.",
                "prediction": "CCNE1-amplified models will show greater CDK2 or PKMYT1 dependency than matched copy-neutral models.",
                "falsifier": "Amplified models lack elevated CCNE1 dosage or selective CDK2/PKMYT1 response.",
                "required_validation": "Confirm focal amplification and expression, then matched perturbation and rescue.",
            },
        ),
    },
    {
        "name": "Loss Cartographers",
        "color": "#71E6E1",
        "agent_id": "agent_7333333333334333b333333333333333",
        "program": "deletion-vulnerability",
        "systems": (
            {
                "node_id": "node_3333333333334333b333333333333333",
                "finding_id": "find_7333333333334333b333333333333333",
                "title": "CDKN2A-loss checkpoint vulnerability",
                "alteration_direction": "loss",
                "genes": ["CDKN2A"],
                "cytobands": ["9p21.3"],
                "mechanisms": ["cell-cycle", "checkpoint-loss"],
                "therapeutic_modalities": ["checkpoint-dependency"],
                "validation_modalities": ["focality", "dosage", "restoration", "drug-response"],
                "summary": "CDKN2A loss occurred in 31.7% and deep loss in 7.3% of tumors; test checkpoint dependencies in confirmed biallelic-loss models.",
                "prediction": "Confirmed CDKN2A-null models will show a reproducible checkpoint dependency reversible by CDKN2A restoration.",
                "falsifier": "Restoration does not alter the dependency or the response is equally present in matched intact models.",
                "required_validation": "Resolve deletion/mutation/methylation state, restore CDKN2A, and compare matched drug response.",
            },
            {
                "node_id": "node_44444444444444448444444444444444",
                "finding_id": "find_74444444444444448444444444444444",
                "title": "ARID1A-loss chromatin synthetic lethality",
                "alteration_direction": "loss",
                "genes": ["ARID1A"],
                "cytobands": ["1p36.11"],
                "mechanisms": ["chromatin-remodeling", "synthetic-lethality"],
                "therapeutic_modalities": ["ATR-inhibition"],
                "validation_modalities": ["focality", "dosage", "restoration", "CRISPR"],
                "summary": "ARID1A loss occurred in 19.4% of tumors; test chromatin/replication-stress synthetic lethality only after confirming functional loss.",
                "prediction": "Functionally ARID1A-deficient models will show selective ATR-pathway vulnerability reversible by ARID1A restoration.",
                "falsifier": "Isogenic restoration fails to rescue the response or intact models are equally sensitive.",
                "required_validation": "Integrate mutation/protein state, use isogenic restoration, then orthogonal CRISPR and pharmacology.",
            },
        ),
    },
    {
        "name": "Constellation Pact",
        "color": "#B98CFF",
        "agent_id": "agent_75555555555545559555555555555555",
        "program": "co-alteration-combination",
        "systems": (
            {
                "node_id": "node_55555555555545559555555555555555",
                "finding_id": "find_75555555555545559555555555555555",
                "title": "ERBB2–CCNE1 dual-program combination",
                "alteration_direction": "co-gain",
                "genes": ["ERBB2", "CCNE1"],
                "cytobands": ["17q12", "19q12"],
                "mechanisms": ["receptor-signaling", "cell-cycle", "combination-dependency"],
                "therapeutic_modalities": ["HER2-blockade", "CDK2-inhibition"],
                "validation_modalities": ["burden-adjustment", "dosage", "combination-response"],
                "summary": "ERBB2 and CCNE1 gains co-occurred in 28 tumors (exploratory OR 4.55); test dual blockade after burden and focality adjustment.",
                "prediction": "Dual-amplified models will show greater-than-single-agent response to HER2 plus CDK2-pathway blockade.",
                "falsifier": "Association disappears after CNA-burden adjustment or dual-amplified models show no combination-specific response.",
                "required_validation": "Adjust for global CNA burden, confirm independent focal peaks/dosage, then factorial combination testing.",
            },
            {
                "node_id": "node_6666666666664666a666666666666666",
                "finding_id": "find_7666666666664666a666666666666666",
                "title": "TERT–RICTOR co-gain combination dependency",
                "alteration_direction": "co-gain",
                "genes": ["TERT", "RICTOR"],
                "cytobands": ["5p15.33", "5p13.1"],
                "mechanisms": ["telomere-maintenance", "mTORC2-signaling", "combination-dependency"],
                "therapeutic_modalities": ["mTORC2-inhibition", "telomerase-strategy"],
                "validation_modalities": ["burden-adjustment", "dosage", "combination-response"],
                "summary": "TERT and RICTOR gains co-occurred in 48 tumors (exploratory OR 83.62); separate shared 5p gain from functional cooperation.",
                "prediction": "If the co-gain is functional rather than physical linkage, dual-positive models will depend on both telomere maintenance and mTORC2 signaling.",
                "falsifier": "The association is explained by one broad 5p event or perturbing one program does not differentially affect dual-positive models.",
                "required_validation": "Segment-level breakpoint mapping, arm/burden-adjusted association, dosage confirmation, and factorial perturbation.",
            },
        ),
    },
)


def validate_summary(summary: dict[str, Any]) -> None:
    if int(summary.get("sample_count", -1)) != EXPECTED_SAMPLES:
        raise RuntimeError(f"Expected {EXPECTED_SAMPLES} tumors")
    if int(summary.get("gene_count", -1)) != EXPECTED_GENES:
        raise RuntimeError(f"Expected {EXPECTED_GENES} genes")
    if len(summary.get("top_amplifications", [])) < 10 or len(summary.get("top_losses", [])) < 10:
        raise RuntimeError("The aggregate STAD summary is incomplete")


def semantic_signature(empire: dict[str, Any], system: dict[str, Any]) -> dict[str, Any]:
    return {
        "program": empire["program"],
        "alteration_direction": system["alteration_direction"],
        "genes": system["genes"],
        "cytobands": system["cytobands"],
        "mechanisms": system["mechanisms"],
        "therapeutic_modalities": system["therapeutic_modalities"],
        "validation_modalities": system["validation_modalities"],
    }


def execute(database: Path, summary_path: Path, output_path: Path) -> dict[str, Any]:
    os.environ["ASTERISM_DATABASE_URL"] = f"sqlite:///{database.resolve().as_posix()}"
    os.environ["ASTERISM_ARTIFACT_ROOT"] = str((database.parent / "artifacts").resolve())

    from asterism_api.database import SessionLocal, init_database
    from asterism_api.db_models import RunRecord
    from asterism_api.event_store import EventStore, make_event
    from asterism_api.multiplayer import (
        claim_node,
        create_host_session,
        join_host,
        publish_finding,
        session_snapshot,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validate_summary(summary)
    run_id = str(summary.get("run_id", ""))
    if not run_id:
        raise RuntimeError("The aggregate summary does not identify its Evolastra run")

    init_database()
    with SessionLocal() as db:
        run = db.get(RunRecord, run_id)
        if run is None:
            raise RuntimeError(f"STAD run {run_id} is not present in {database}")
        root = next(
            (node for node in run.state.get("nodes", {}).values() if not node.get("parent_node_id")),
            None,
        )
        if not root:
            raise RuntimeError("The STAD run has no root analysis system")
        store = EventStore(db)

        for empire in EMPIRES:
            agent = {
                "id": empire["agent_id"],
                "schema_version": 1,
                "run_id": run_id,
                "parent_agent_id": None,
                "name": f"{empire['name']} mothership",
                "role": f"{empire['program']} research commander",
                "framework": "Evolastra multiplayer simulation",
                "status": "completed",
                "current_node_id": empire["systems"][0]["node_id"],
                "ship_blueprint_id": "mothership",
                "ship_hull": "mothership",
                "capabilities": [empire["program"], "falsification", "matched validation"],
            }
            if empire["agent_id"] not in run.state.get("agents", {}):
                result = store.ingest(make_event(
                    run_id=run_id,
                    event_type="galaxy.analysis.agent.created.v1",
                    subject=f"run/{run_id}/agent/{empire['agent_id']}",
                    data={"agent": agent},
                    source="urn:evolastra:stad-multiplayer-simulation",
                ).model_dump(mode="json"))
                if not result.accepted:
                    raise RuntimeError(result.reason or "Empire agent could not be recorded")
            db.expire_all()
            run = db.get(RunRecord, run_id)
            if run is None:
                raise RuntimeError("STAD run disappeared during agent launch")
            current_agent = run.state.get("agents", {}).get(empire["agent_id"], {})
            if current_agent.get("status") != "running":
                result = store.ingest(make_event(
                    run_id=run_id,
                    event_type="galaxy.analysis.agent.started.v1",
                    subject=f"run/{run_id}/agent/{empire['agent_id']}",
                    data={"agent": {**agent, "status": "running"}},
                    source="urn:evolastra:stad-multiplayer-simulation",
                ).model_dump(mode="json"))
                if not result.accepted:
                    raise RuntimeError(result.reason or "Empire agent could not be launched")

            for system in empire["systems"]:
                node = {
                    "id": system["node_id"],
                    "schema_version": 1,
                    "run_id": run_id,
                    "parent_node_id": root["id"],
                    "node_type": "exploratory_hypothesis",
                    "title": system["title"],
                    "description": f"{system['summary']} Falsifier: {system['falsifier']}",
                    "explicit_objective": system["prediction"],
                    "status": "completed",
                    "priority": "high",
                    "phase": "hypothesis-generation",
                    "topic": empire["program"],
                    "assigned_agent_ids": [empire["agent_id"]],
                    "creation_source": "three-empire-multiplayer-simulation",
                    "promotion_reason": "distinct falsifiable exploratory CNA direction",
                    "progress": 1.0,
                    "tags": ["STAD", "CNA", "exploratory", empire["program"]],
                    "semantic_signature": semantic_signature(empire, system),
                    "prediction": system["prediction"],
                    "falsifier": system["falsifier"],
                    "required_validation": system["required_validation"],
                }
                db.expire_all()
                run = db.get(RunRecord, run_id)
                if run is None:
                    raise RuntimeError("STAD run disappeared during simulation")
                if system["node_id"] not in run.state.get("nodes", {}):
                    result = store.ingest(make_event(
                        run_id=run_id,
                        event_type="galaxy.analysis.node.created.v1",
                        subject=f"run/{run_id}/node/{system['node_id']}",
                        data={"node": node},
                        source="urn:evolastra:stad-multiplayer-simulation",
                    ).model_dump(mode="json"))
                    if not result.accepted:
                        raise RuntimeError(result.reason or "Hypothesis system could not be recorded")
                db.expire_all()
                run = db.get(RunRecord, run_id)
                if run is None:
                    raise RuntimeError("STAD run disappeared during hypothesis launch")
                current_node = run.state.get("nodes", {}).get(system["node_id"], {})
                if current_node.get("status") != "running":
                    result = store.ingest(make_event(
                        run_id=run_id,
                        event_type="galaxy.analysis.node.started.v1",
                        subject=f"run/{run_id}/node/{system['node_id']}",
                        data={"node": {**node, "status": "running", "progress": 0.42}},
                        source="urn:evolastra:stad-multiplayer-simulation",
                    ).model_dump(mode="json"))
                    if not result.accepted:
                        raise RuntimeError(result.reason or "Hypothesis system could not be launched")

                finding = {
                    "id": system["finding_id"],
                    "schema_version": 1,
                    "run_id": run_id,
                    "node_id": system["node_id"],
                    "title": system["title"],
                    "summary": system["summary"],
                    "claim_ids": [],
                    "evidence_ids": [],
                    "artifact_ids": [],
                    "validation_status": "provisional",
                    "importance": "exploratory",
                    "reproducible": True,
                    "exploratory": True,
                    "prediction": system["prediction"],
                    "falsifier": system["falsifier"],
                    "required_validation": system["required_validation"],
                }
                db.expire_all()
                run = db.get(RunRecord, run_id)
                if run is None:
                    raise RuntimeError("STAD run disappeared during simulation")
                if system["finding_id"] not in run.state.get("findings", {}):
                    result = store.ingest(make_event(
                        run_id=run_id,
                        event_type="galaxy.analysis.finding.created.v1",
                        subject=f"run/{run_id}/finding/{system['finding_id']}",
                        data={"finding": finding},
                        source="urn:evolastra:stad-multiplayer-simulation",
                    ).model_dump(mode="json"))
                    if not result.accepted:
                        raise RuntimeError(result.reason or "Exploratory finding could not be recorded")

        db.expire_all()
        run = db.get(RunRecord, run_id)
        if run is None:
            raise RuntimeError("STAD run disappeared before multiplayer setup")
        host_session, _invite = create_host_session(
            db,
            run=run,
            display_name=EMPIRES[0]["name"],
            color=EMPIRES[0]["color"],
            share_url="https://stad-semantic-simulation.ts.net",
        )
        host_session.remote_state = {
            "simulation_active": True,
            "simulation_label": "Three-empire STAD semantic frontier",
        }
        db.commit()
        players = {EMPIRES[0]["name"]: host_session.local_player_id}
        for empire in EMPIRES[1:]:
            player, _member_token = join_host(
                db,
                session=host_session,
                display_name=empire["name"],
                color=empire["color"],
                fingerprint=host_session.project_fingerprint,
            )
            players[empire["name"]] = player.id

        for empire in EMPIRES:
            player_id = players[empire["name"]]
            for system in empire["systems"]:
                claim_node(db, session=host_session, player_id=player_id, node_id=system["node_id"])
                publish_finding(
                    db,
                    session=host_session,
                    player_id=player_id,
                    finding_id=system["finding_id"],
                    title=system["title"],
                    summary=system["summary"],
                )

        snapshot = session_snapshot(db, host_session)
        hypothesis_ids = {system["node_id"] for empire in EMPIRES for system in empire["systems"]}
        hypothesis_claims = [claim for claim in snapshot["claims"] if claim["node_id"] in hypothesis_ids]
        result = {
            "schema_version": 1,
            "status": "exploratory-simulation-complete",
            "run_id": run_id,
            "source": {
                "summary": str(summary_path.resolve()),
                "matrix_sha256": EXPECTED_SHA256,
                "sample_count": EXPECTED_SAMPLES,
                "gene_count": EXPECTED_GENES,
            },
            "seed": 874049,
            "players": snapshot["players"],
            "hypothesis_claims": hypothesis_claims,
            "capital_claims": [claim for claim in snapshot["claims"] if claim["node_id"] not in hypothesis_ids],
            "publications": snapshot["publications"],
            "hypotheses": [
                {
                    "empire": empire["name"],
                    "color": empire["color"],
                    "node_id": system["node_id"],
                    "finding_id": system["finding_id"],
                    "title": system["title"],
                    "semantic_signature": semantic_signature(empire, system),
                    "prediction": system["prediction"],
                    "falsifier": system["falsifier"],
                    "required_validation": system["required_validation"],
                }
                for empire in EMPIRES
                for system in empire["systems"]
            ],
            "layout_validation": None,
            "interpretation": "Exploratory hypothesis generation; no causal, therapeutic-efficacy, or novelty claim.",
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local three-empire STAD multiplayer simulation")
    parser.add_argument("--database", type=Path, default=Path("data/live-test/evolastra.db"))
    parser.add_argument("--summary", type=Path, default=Path("data/live-test/stad_cna_live_summary.json"))
    parser.add_argument("--output", type=Path, default=Path("data/live-test/stad_multiplayer_simulation.json"))
    parser.add_argument("--check", action="store_true", help="Validate aggregate inputs without changing the database")
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    validate_summary(summary)
    if args.check:
        print(json.dumps({"ok": True, "sample_count": EXPECTED_SAMPLES, "gene_count": EXPECTED_GENES, "empires": len(EMPIRES), "systems": sum(len(empire["systems"]) for empire in EMPIRES)}))
        return
    result = execute(args.database, args.summary, args.output)
    print(json.dumps({"status": result["status"], "players": len(result["players"]), "hypothesis_claims": len(result["hypothesis_claims"]), "publications": len(result["publications"]), "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
