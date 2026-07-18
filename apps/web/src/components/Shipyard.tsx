import { useEffect, useMemo, useState } from "react";
import { buildShip, dispatchShip, fetchShipyard } from "../api";
import type { Entity, MissionReceipt, ShipBlueprint, ShipyardState } from "../types";
import { StatusMark } from "./StatusMark";

interface ShipyardProps {
  open: boolean;
  runId: string | null;
  preferredBlueprintId: string | null;
  onClose: () => void;
  onChanged: () => void;
}

function shipBlueprintId(ship: Entity): string {
  return String(ship.ship_blueprint_id ?? "");
}

function HullFigure({ hull }: { hull: ShipBlueprint["hull"] }) {
  return <span className={`hull-figure hull-${hull}`} aria-hidden="true"><i /><i /><i /></span>;
}

export function Shipyard({ open, runId, preferredBlueprintId, onClose, onChanged }: ShipyardProps) {
  const [yard, setYard] = useState<ShipyardState | null>(null);
  const [selectedBlueprintId, setSelectedBlueprintId] = useState<string>("frigate");
  const [selectedShipId, setSelectedShipId] = useState<string>("");
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState<"loading" | "building" | "dispatching" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<MissionReceipt | null>(null);

  const refresh = async (preferredShipId?: string, blueprintOverride?: string) => {
    if (!runId) return;
    const state = await fetchShipyard(runId);
    setYard(state);
    const preferredBlueprint = blueprintOverride && state.blueprints.some((item) => item.id === blueprintOverride)
      ? blueprintOverride
      : selectedBlueprintId;
    if (state.blueprints.some((item) => item.id === preferredBlueprint)) setSelectedBlueprintId(preferredBlueprint);
    const compatible = state.ships.filter((ship) => shipBlueprintId(ship) === preferredBlueprint);
    const nextShip = preferredShipId ?? (compatible.some((ship) => ship.id === selectedShipId) ? selectedShipId : compatible[0]?.id ?? "");
    setSelectedShipId(nextShip);
  };

  useEffect(() => {
    if (!open || !runId) return;
    setBusy("loading");
    setError(null);
    setReceipt(null);
    void refresh(undefined, preferredBlueprintId ?? "frigate").catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Shipyard status could not be loaded");
    }).finally(() => setBusy(null));
  // The shipyard deliberately refreshes from the server whenever it opens.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, runId, preferredBlueprintId]);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [busy, onClose, open]);

  const selectedBlueprint = yard?.blueprints.find((item) => item.id === selectedBlueprintId) ?? null;
  const compatibleShips = useMemo(
    () => yard?.ships.filter((ship) => shipBlueprintId(ship) === selectedBlueprintId) ?? [],
    [selectedBlueprintId, yard?.ships],
  );
  const selectedShip = yard?.ships.find((ship) => ship.id === selectedShipId) ?? null;

  useEffect(() => {
    if (compatibleShips.some((ship) => ship.id === selectedShipId)) return;
    setSelectedShipId(compatibleShips[0]?.id ?? "");
  }, [compatibleShips, selectedShipId]);

  if (!open) return null;

  const build = async () => {
    if (!runId || !selectedBlueprint) return;
    setBusy("building");
    setError(null);
    setReceipt(null);
    try {
      const result = await buildShip(runId, selectedBlueprint.id);
      await refresh(result.ship.id);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ship construction failed");
    } finally {
      setBusy(null);
    }
  };

  const dispatch = async () => {
    if (!runId || !selectedShip || prompt.trim().length < 3) return;
    setBusy("dispatching");
    setError(null);
    setReceipt(null);
    try {
      const result = await dispatchShip(runId, selectedShip.id, prompt.trim());
      setReceipt(result);
      setPrompt("");
      await refresh(selectedShip.id);
      onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Mission launch failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="shipyard-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
      <section className="shipyard" role="dialog" aria-modal="true" aria-labelledby="shipyard-title">
        <header className="shipyard-head">
          <div><span className="eyebrow">COMMAND STAR · ORBITAL DRYDOCK</span><h2 id="shipyard-title">Build a Codex vessel</h2><p>Choose a hull, commission a ship, then give it one explicit mission.</p></div>
          <button className="icon-button" onClick={onClose} disabled={Boolean(busy)} aria-label="Close shipyard" autoFocus>×</button>
        </header>

        {busy === "loading" || !yard ? <div className="shipyard-loading"><span className="orbit-loader" /><p>Reading available hulls…</p></div> : <>
          <div className="shipyard-safety" aria-label="Mission safety boundary">
            <span><i /> Signed-in Codex</span><span><i /> Local stdio</span><span><i /> Fixed workspace</span><span><i /> No escalation</span>
          </div>

          <div className="shipyard-grid">
            <section className="blueprint-rack" aria-labelledby="blueprint-title">
              <div className="shipyard-section-title"><span><b>01</b></span><div><small>FLIGHT LINE</small><h3 id="blueprint-title">Select a blueprint</h3></div></div>
              <div className="blueprint-list">
                {yard.blueprints.map((blueprint) => <button
                  className={`blueprint-card${blueprint.id === selectedBlueprintId ? " selected" : ""}`}
                  aria-pressed={blueprint.id === selectedBlueprintId}
                  key={blueprint.id}
                  onClick={() => { setSelectedBlueprintId(blueprint.id); setReceipt(null); }}
                >
                  <HullFigure hull={blueprint.hull} />
                  <span><small>{blueprint.source_node_id ? "RESEARCH HULL" : "CORE HULL"}</small><strong>{blueprint.name}</strong><em>{blueprint.role}</em></span>
                  {blueprint.source_node_id && <b>UNLOCKED</b>}
                </button>)}
              </div>
            </section>

            <section className="drydock-console" aria-labelledby="drydock-title">
              <div className="shipyard-section-title"><span><b>02</b></span><div><small>DRYDOCK</small><h3 id="drydock-title">Commission and launch</h3></div></div>
              {selectedBlueprint && <div className="selected-hull">
                <div className="launch-ring"><HullFigure hull={selectedBlueprint.hull} /></div>
                <div><span className="eyebrow">{selectedBlueprint.hull.toUpperCase()} BLUEPRINT</span><h3>{selectedBlueprint.name}</h3><p>{selectedBlueprint.description}</p><ul>{selectedBlueprint.capabilities.map((capability) => <li key={capability}>{capability}</li>)}</ul></div>
              </div>}

              <div className="commission-row">
                <button className="primary-button" onClick={() => void build()} disabled={Boolean(busy) || !selectedBlueprint}>{busy === "building" ? "Constructing…" : `Build ${selectedBlueprint?.name ?? "ship"}`}</button>
                <span>{compatibleShips.length} commissioned</span>
              </div>

              <div className="mission-field"><label htmlFor="mission-vessel">Mission vessel</label>
                <select id="mission-vessel" value={selectedShipId} onChange={(event) => setSelectedShipId(event.target.value)}>
                  <option value="">Build this hull first</option>
                  {compatibleShips.map((ship) => <option value={ship.id} key={ship.id}>{String(ship.name ?? ship.id)} · {String(ship.status ?? "created")}</option>)}
                </select>
              </div>
              <div className="mission-field"><label htmlFor="mission-order">Mission order</label>
                <textarea id="mission-order" value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={8_000} placeholder={selectedBlueprint?.hull === "colony" ? "Explore a novel, testable direction for…" : selectedBlueprint?.hull === "mothership" ? "Coordinate parallel agents to…" : "Investigate, build, or verify…"} />
                <small>{prompt.length.toLocaleString()} / 8,000 · sent only to the local companion and signed-in Codex</small>
              </div>
              <button className="launch-button" onClick={() => void dispatch()} disabled={Boolean(busy) || !selectedShip || prompt.trim().length < 3 || !yard.codex_available}>
                <span aria-hidden="true">▶</span>{busy === "dispatching" ? "Opening Codex task…" : "Launch mission"}
              </button>
              {!yard.codex_available && <p className="shipyard-warning">Codex dispatch is offline. Start the installed Local Private companion with the Codex CLI available.</p>}
              {error && <p className="shipyard-error" role="alert">{error}</p>}
              {receipt && <div className="launch-receipt" role="status"><StatusMark status="running" /><span><strong>Mission launched</strong><small>Codex task {receipt.thread_id}</small></span></div>}
            </section>
          </div>
        </>}
      </section>
    </div>
  );
}
