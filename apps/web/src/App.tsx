import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { downloadExport, fetchMultiplayerState, fetchState, importPortableAnalysis, listRuns, pairingInfo, search, sendCommand } from "./api";
import { ArtifactPreview } from "./components/ArtifactPreview";
import { ConnectionPanel } from "./components/ConnectionPanel";
import { Explorer } from "./components/Explorer";
import { GalaxyCanvas } from "./components/GalaxyCanvas";
import { Inspector } from "./components/Inspector";
import { MapBrief } from "./components/MapBrief";
import { MultiplayerPanel } from "./components/MultiplayerPanel";
import { ReplayTransport } from "./components/ReplayTransport";
import { Shipyard } from "./components/Shipyard";
import { StatusMark } from "./components/StatusMark";
import { WorkspaceView } from "./components/WorkspaceView";
import { useLiveProjection } from "./hooks/useLiveProjection";
import { advanceReplay, replayStart } from "./replay";
import { AUTH_REQUIRED_EVENT, CONNECTION_CHANGED_EVENT, getConnection } from "./connection";
import { parseSemanticSignature } from "./semanticLayout";
import { loadPublicShowcase, searchPublicShowcase, showcaseMultiplayerAtState, showcasePhaseLabel, showcaseStateAtSequence, type PublicShowcaseBundle } from "./showcase";
import type { Entity, GraphState, MultiplayerState, RunSummary, SceneEntity, ViewName } from "./types";

const PRIMARY_VIEWS: Array<{ id: ViewName; label: string }> = [
  { id: "galaxy", label: "Galaxy map" },
  { id: "system", label: "System view" },
  { id: "advanced", label: "Advanced" },
];

const ADVANCED_VIEWS: Array<{ id: ViewName; label: string }> = [
  { id: "tree", label: "Tech tree" },
  { id: "findings", label: "Findings" },
  { id: "timeline", label: "Timeline" },
  { id: "agents", label: "Agents" },
  { id: "artifacts", label: "Figures" },
  { id: "datasets", label: "Data" },
  { id: "metrics", label: "Metrics" },
  { id: "telemetry", label: "Telemetry" },
  { id: "comparison", label: "Compare" },
];

export function sceneFromState(state: GraphState): { entities: SceneEntity[]; rootId: string } {
  const rootNode = state.nodes.find((node) => !node.parent_node_id);
  const rootId = rootNode?.id ?? state.run.id;
  const root: SceneEntity = {
    id: rootId,
    title: String(rootNode?.title ?? state.run.title ?? "Home system"),
    kind: "home",
    status: String(rootNode?.status ?? state.run.status ?? "running"),
    progress: Number(rootNode?.progress ?? 0),
    sequence: Number(rootNode?._sequence ?? 0),
  };
  const nodes: SceneEntity[] = state.nodes
    .filter((node) => node.id !== rootId)
    .map((node) => ({ id: node.id, title: String(node.title ?? node.id), kind: "node", status: String(node.status ?? "created"), parentId: node.parent_node_id || rootId, progress: node.progress, sequence: node._sequence, semanticSignature: parseSemanticSignature(node.semantic_signature) }));
  const artifacts: SceneEntity[] = state.artifacts.map((artifact) => ({ id: artifact.id, title: String(artifact.title ?? artifact.id), kind: "artifact", status: String(artifact.status ?? "created"), parentId: String(artifact.node_id ?? rootId), sequence: artifact._sequence }));
  const findings: SceneEntity[] = state.findings.map((finding) => ({ id: finding.id, title: String(finding.title ?? finding.id), kind: "finding", status: String(finding.status ?? finding.validation_status ?? "created"), parentId: String(finding.node_id ?? rootId), sequence: finding._sequence }));
  const anomalies: SceneEntity[] = state.anomalies.map((anomaly) => ({ id: anomaly.id, title: String(anomaly.title ?? anomaly.id), kind: "anomaly", status: String(anomaly.status ?? "created"), parentId: String(anomaly.node_id ?? rootId), sequence: anomaly._sequence }));
  const agents: SceneEntity[] = state.agents.map((agent) => ({ id: agent.id, title: String(agent.name ?? agent.id), kind: "agent", status: String(agent.status ?? "created"), parentId: String(agent.current_node_id ?? rootId), sequence: agent._sequence }));
  const toolCalls: SceneEntity[] = state.tool_calls.map((tool) => ({ id: tool.id, title: String(tool.tool_name ?? "Tool call"), kind: "tool", status: String(tool.status ?? "requested"), parentId: String(tool.node_id ?? rootId), sequence: tool._sequence }));
  return { entities: [root, ...nodes, ...artifacts, ...findings, ...anomalies, ...agents, ...toolCalls], rootId };
}

export function userVisibleRuns(runs: RunSummary[], includeDevelopmentDemos = false): RunSummary[] {
  return includeDevelopmentDemos ? runs : runs.filter((run) => !run.tags?.includes("seeded-demo"));
}

export default function App() {
  const [connectionRevision, setConnectionRevision] = useState(0);
  const [connectionOpen, setConnectionOpen] = useState(false);
  const [connectionRequired, setConnectionRequired] = useState(false);
  const [connectionReady, setConnectionReady] = useState(false);
  const [showcase, setShowcase] = useState<PublicShowcaseBundle | null>(null);
  const showcaseActive = showcase !== null;
  const runsQuery = useQuery({ queryKey: ["runs", connectionRevision], queryFn: listRuns, refetchInterval: connectionRequired ? false : 1_500, retry: false, enabled: connectionReady && !connectionRequired && !showcaseActive });
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [view, setView] = useState<ViewName>("galaxy");
  const [advancedView, setAdvancedView] = useState<ViewName>("findings");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [animationPaused, setAnimationPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [highContrast, setHighContrast] = useState(false);
  const [replaySequence, setReplaySequence] = useState<number | null>(null);
  const [replayState, setReplayState] = useState<GraphState | null>(null);
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [replayRate, setReplayRate] = useState(1);
  const [artifact, setArtifact] = useState<Entity | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Array<{ id: string; entity_type: string; title: string; context: string }>>([]);
  const [transferStatus, setTransferStatus] = useState<{ error: boolean; text: string } | null>(null);
  const [shipyardOpen, setShipyardOpen] = useState(false);
  const [shipyardBlueprintId, setShipyardBlueprintId] = useState<string | null>(null);
  const [multiplayerOpen, setMultiplayerOpen] = useState(false);
  const portableInput = useRef<HTMLInputElement>(null);
  const includeDevelopmentDemos = import.meta.env.DEV && new URLSearchParams(window.location.search).get("development-demo") === "1";

  useEffect(() => {
    const requireConnection = () => { setConnectionRequired(true); setConnectionOpen(true); };
    const connectionChanged = () => setConnectionRevision((value) => value + 1);
    window.addEventListener(AUTH_REQUIRED_EVENT, requireConnection);
    window.addEventListener(CONNECTION_CHANGED_EVENT, connectionChanged);
    return () => {
      window.removeEventListener(AUTH_REQUIRED_EVENT, requireConnection);
      window.removeEventListener(CONNECTION_CHANGED_EVENT, connectionChanged);
    };
  }, []);

  useEffect(() => {
    if (showcaseActive) return;
    let active = true;
    void pairingInfo().then((info) => {
      if (!active) return;
      if (info.authentication_required && !getConnection().token) {
        setConnectionRequired(true);
        setConnectionOpen(true);
        setConnectionReady(false);
      } else setConnectionReady(true);
    }).catch(() => {
      if (!active) return;
      setConnectionRequired(true);
      setConnectionOpen(true);
      setConnectionReady(false);
    });
    return () => { active = false; };
  }, [connectionRevision, showcaseActive]);

  useEffect(() => {
    if (showcaseActive) return;
    const runs = userVisibleRuns(runsQuery.data ?? [], includeDevelopmentDemos);
    if (!activeRunId && runs.length) setActiveRunId(runs[0].id);
  }, [activeRunId, includeDevelopmentDemos, runsQuery.data, showcaseActive]);

  const live = useLiveProjection(showcaseActive ? null : activeRunId, connectionRevision);
  const multiplayerQuery = useQuery({
    queryKey: ["multiplayer", activeRunId, connectionRevision],
    queryFn: () => fetchMultiplayerState(activeRunId!),
    enabled: Boolean(activeRunId && connectionReady && !connectionRequired && !showcaseActive),
    refetchInterval: 5_000,
    retry: false,
  });
  useEffect(() => {
    if (!live.state || selectedId) return;
    const root = live.state.nodes.find((node) => !node.parent_node_id);
    setSelectedId(root?.id ?? live.state.run.id);
  }, [live.state, selectedId]);

  useEffect(() => {
    if (showcaseActive || !activeRunId || replaySequence === null) {
      setReplayState(null);
      return;
    }
    let active = true;
    const timer = window.setTimeout(() => void fetchState(activeRunId, replaySequence).then((state) => { if (active) setReplayState(state); }), 80);
    return () => { active = false; window.clearTimeout(timer); };
  }, [activeRunId, replaySequence, showcaseActive]);

  const latestSequence = Math.max(1, showcase?.state.last_sequence ?? live.state?.last_sequence ?? 1);
  const replayStatus = showcase && replaySequence === null
    ? `PUBLIC EXPEDITION · ${latestSequence} PHASES COMPLETE`
    : showcase && replaySequence !== null
      ? `${replayPlaying ? "PLAYING" : "REPLAY PAUSED"} · PHASE ${replaySequence} / ${latestSequence} · ${showcasePhaseLabel(showcase, replaySequence)}`
      : replaySequence === null
        ? "LIVE EVENT HORIZON"
        : `${replayPlaying ? "PLAYING" : "REPLAY PAUSED"} · EVENT ${replaySequence} / ${latestSequence}`;

  useEffect(() => {
    if (!replayPlaying || replaySequence === null) return;
    if (replaySequence >= latestSequence) {
      setReplayPlaying(false);
      const timer = window.setTimeout(() => {
        setReplaySequence(null);
        setReplayState(null);
      }, 420);
      return () => window.clearTimeout(timer);
    }
    const timer = window.setInterval(() => {
      setReplaySequence((current) => current === null ? 1 : advanceReplay(current, latestSequence, replayRate));
    }, 240);
    return () => window.clearInterval(timer);
  }, [latestSequence, replayPlaying, replayRate, replaySequence]);

  useEffect(() => {
    setReplayPlaying(false);
  }, [activeRunId]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
      if (event.key === "Escape") { setSearchOpen(false); setArtifact(null); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (!activeRunId || searchQuery.trim().length < 2) { setSearchResults([]); return; }
    if (showcase) {
      setSearchResults(searchPublicShowcase(showcaseStateAtSequence(showcase, replaySequence), searchQuery));
      return;
    }
    let active = true;
    const timer = window.setTimeout(() => void search(activeRunId, searchQuery.trim()).then((items) => { if (active) setSearchResults(items); }), 180);
    return () => { active = false; window.clearTimeout(timer); };
  }, [activeRunId, replaySequence, searchQuery, showcase]);

  const state = showcase ? showcaseStateAtSequence(showcase, replaySequence) : replaySequence === null ? live.state : replayState ?? live.state;
  const scene = useMemo(() => state ? sceneFromState(state) : null, [state]);
  const focusSystemId = useMemo(() => {
    if (!scene) return "";
    const selected = scene.entities.find((entity) => entity.id === selectedId);
    if (selected && ["home", "node"].includes(selected.kind)) return selected.id;
    if (selected?.parentId && scene.entities.some((entity) => entity.id === selected.parentId && ["home", "node"].includes(entity.kind))) return selected.parentId;
    return scene.rootId;
  }, [scene, selectedId]);
  const runs = showcase ? [showcase.run] : userVisibleRuns(runsQuery.data ?? [], includeDevelopmentDemos);
  const run = showcase?.run ?? runs.find((item) => item.id === activeRunId);
  const runSeed = Number(state?.run.run_seed ?? run?.seed ?? 1);
  const streamLag = showcaseActive ? 0 : Math.max(0, (run?.last_sequence ?? live.state?.last_sequence ?? 0) - (live.state?.last_sequence ?? 0));
  const multiplayer = showcase && state ? showcaseMultiplayerAtState(showcase, state) : multiplayerQuery.data ?? ({ enabled: false } satisfies MultiplayerState);
  const claimColors = useMemo(() => {
    const playerColors = new Map((multiplayer.players ?? []).map((player) => [player.id, player.color]));
    return Object.fromEntries((multiplayer.claims ?? []).flatMap((claim) => {
      const color = playerColors.get(claim.player_id);
      return color ? [[claim.node_id, color]] : [];
    }));
  }, [multiplayer.claims, multiplayer.players]);
  const selectedSystem = useMemo(() => {
    const selected = scene?.entities.find((entity) => entity.id === selectedId);
    return selected && ["home", "node"].includes(selected.kind) ? { id: selected.id, title: selected.title } : null;
  }, [scene, selectedId]);
  const advanced = view === "advanced";
  const openShipyard = (blueprintId: string | null = null) => {
    if (showcaseActive) return;
    setShipyardBlueprintId(blueprintId);
    setShipyardOpen(true);
  };
  const enterShowcase = async () => {
    const bundle = await loadPublicShowcase();
    setShowcase(bundle);
    setConnectionOpen(false);
    setConnectionRequired(false);
    setConnectionReady(false);
    setReplayPlaying(false);
    setReplaySequence(null);
    setReplayState(null);
    setActiveRunId(bundle.run.id);
    setSelectedId("demo_node_capital");
    setView("galaxy");
  };
  const startOrPauseReplay = () => {
    if (replayPlaying) {
      setReplayPlaying(false);
      return;
    }
    setReplaySequence((current) => replayStart(current, latestSequence));
    setReplayPlaying(true);
  };

  const returnLive = () => {
    setReplayPlaying(false);
    setReplaySequence(null);
    setReplayState(null);
  };

  const loadPortableAnalysis = async (file: File) => {
    setTransferStatus({ error: false, text: "Loading analysis…" });
    try {
      const result = await importPortableAnalysis(file);
      setReplayPlaying(false);
      setReplaySequence(null);
      setSelectedId(null);
      setActiveRunId(result.run_id);
      await runsQuery.refetch();
      setTransferStatus({ error: false, text: `Loaded ${result.title ?? "analysis"}` });
    } catch (reason) {
      setTransferStatus({ error: true, text: reason instanceof Error ? reason.message : "Analysis could not be loaded" });
    } finally {
      if (portableInput.current) portableInput.current.value = "";
    }
  };

  return (
    <div className={`app-shell${highContrast ? " high-contrast" : ""}${advanced ? " advanced-mode" : ""}${showcaseActive ? " showcase-mode" : ""}`}>
      <a href="#workspace" className="skip-link">Skip to workspace</a>
      <header className="run-header">
        <div className="brand-lockup" aria-label="Evolastra Observatory">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <div>
            <strong>EVOLASTRA</strong>
            <nav className="brand-links" aria-label="Evolastra project links">
              <a href="https://github.com/Paureel/evolastra" target="_blank" rel="noreferrer" aria-label="Evolastra on GitHub">GITHUB <i aria-hidden="true">↗</i></a>
              <a href="https://x.com/aurel_pr" target="_blank" rel="noreferrer" aria-label="Aurel on X">X @AUREL_PR <i aria-hidden="true">↗</i></a>
            </nav>
          </div>
        </div>
        <div className="run-identity">
          <span className="eyebrow">{showcaseActive ? "PUBLIC SHOWCASE · THREE EMPIRES" : `ACTIVE RUN · ${run?.id.slice(-8).toUpperCase() ?? "CONNECTING"}`}</span>
          <h1>{run?.title ?? (connectionReady && !connectionRequired ? "No active analysis" : "Establishing observatory link")}</h1>
        </div>
        <button className="run-status" aria-label="Connection and local data status" onClick={() => { setConnectionRequired(false); setConnectionOpen(true); }}>
          <StatusMark status={showcaseActive ? "completed" : live.connection === "live" ? "running" : "failed"} label={showcaseActive ? "static · read only" : `${live.connection} · ${streamLag} lag`} />
          <small>{showcaseActive ? "PUBLIC DEMO" : "LOCAL DATA"}</small>
        </button>
        <button className={`federation-trigger${multiplayer.enabled ? ` ${multiplayer.session?.status ?? "paused"}` : ""}`} onClick={() => setMultiplayerOpen(true)} aria-label="Open multiplayer federation">
          <span className="federation-pips" aria-hidden="true">{(multiplayer.players ?? []).slice(0, 4).map((player) => <i key={player.id} style={{ background: player.color }} />)}{!multiplayer.enabled && <i />}</span>
          <strong>{multiplayer.enabled ? `${multiplayer.players?.length ?? 1} players` : "Single player"}</strong><small>{multiplayer.enabled ? multiplayer.session?.status : "MULTIPLAYER"}</small>
        </button>
        <button className="search-trigger" onClick={() => setSearchOpen(true)}><span>Search</span><kbd>Ctrl K</kbd></button>
      </header>

      <div className="view-rail" role="tablist" aria-label="Primary views">
        {PRIMARY_VIEWS.map((item) => <button role="tab" aria-selected={view === item.id} className={view === item.id ? "active" : ""} key={item.id} onClick={() => setView(item.id)}>{item.label}</button>)}
      </div>

      <main id="workspace" className={`observatory-grid ${advanced ? "advanced-layout" : "map-layout"}`}>
        {advanced && (
          <div className="advanced-toolbar">
            <div className="advanced-heading"><span className="eyebrow">ADVANCED WORKSPACE</span><small>Evidence, provenance, and run operations</small></div>
            <div className="advanced-tabs" role="tablist" aria-label="Advanced views">
              {ADVANCED_VIEWS.map((item) => <button role="tab" aria-selected={advancedView === item.id} className={advancedView === item.id ? "active" : ""} key={item.id} onClick={() => setAdvancedView(item.id)}>{item.label}</button>)}
            </div>
          </div>
        )}
        {advanced && <Explorer runs={runs} activeRunId={activeRunId} onRunChange={(id) => { setReplayPlaying(false); setActiveRunId(id); setSelectedId(null); setReplaySequence(null); }} state={state} selectedId={selectedId} onSelect={setSelectedId} />}
        <section className="main-workspace" aria-live="polite">
          {!showcaseActive && live.error && <div className="error-banner" role="alert">Projection link failed: {live.error}. The client will retry.</div>}
          {!state || !scene ? (
            connectionReady && !connectionRequired && runsQuery.isSuccess && runs.length === 0
              ? <div className="workspace-empty analysis-empty"><span className="empty-orbit" /><h2>No analysis yet</h2><p>Start a Codex task in this project, or open the connection panel to explore the public STAD demo.</p></div>
              : <div className="loading-field"><span className="orbit-loader" /><h2>Calibrating semantic projection</h2><p>Durable events remain the source of truth.</p></div>
          ) : !advanced ? (
            <>
              <GalaxyCanvas
                entities={scene.entities}
                edges={state.edges}
                seed={runSeed}
                projectionScope={run?.id ?? activeRunId ?? "pending-run"}
                mode={view === "system" ? "system" : "galaxy"}
                focusSystemId={focusSystemId}
                selectedId={selectedId}
                onSelect={setSelectedId}
                onOpenSystem={(id) => { setSelectedId(id); setView("system"); }}
                onOpenShipyard={() => openShipyard()}
                shipyardEnabled={!showcaseActive && focusSystemId === scene.rootId}
                multiplayerClaims={claimColors}
                onBackToGalaxy={() => setView("galaxy")}
                animated={!animationPaused}
                reducedMotion={reducedMotion}
                highContrast={highContrast}
              />
              <MapBrief
                state={state}
                scene={scene.entities}
                selectedId={selectedId}
                seed={runSeed}
                mode={view === "system" ? "system" : "galaxy"}
                onOpenSystem={(id) => { setSelectedId(id); setView("system"); }}
                onOpenShipyard={() => openShipyard()}
                onOpenAdvanced={() => setView("advanced")}
                readOnly={showcaseActive}
              />
              {view === "galaxy" && <aside className="galaxy-replay-dock" aria-label="Galaxy timeline">
                <ReplayTransport
                  compact
                  playing={replayPlaying}
                  sequence={replaySequence}
                  latestSequence={latestSequence}
                  status={replayStatus}
                  unitLabel={showcaseActive ? "Phase" : "Event"}
                  rangeLabel={showcaseActive ? "Replay phase" : "Replay sequence"}
                  onToggle={startOrPauseReplay}
                  onLive={returnLive}
                  onSequenceChange={(sequence) => { setReplayPlaying(false); setReplaySequence(sequence); }}
                />
              </aside>}
            </>
          ) : <WorkspaceView view={advancedView} state={state} runs={runs} currentRunId={activeRunId} onSelect={setSelectedId} onOpenShipyard={(blueprintId) => openShipyard(blueprintId)} onOpenArtifact={setArtifact} readOnly={showcaseActive} />}
        </section>
        {advanced && <Inspector state={state} selectedId={selectedId} onRefresh={live.refresh} onOpenArtifact={setArtifact} onOpenSystem={(id) => { setSelectedId(id); setView("system"); }} spaceMode={null} />}
      </main>

      {advanced && <footer className="timeline-dock" aria-label="Advanced run controls">
        <ReplayTransport
          playing={replayPlaying}
          sequence={replaySequence}
          latestSequence={latestSequence}
          status={replayStatus}
          unitLabel={showcaseActive ? "Phase" : "Event"}
          rangeLabel={showcaseActive ? "Replay phase" : "Replay sequence"}
          onToggle={startOrPauseReplay}
          onLive={returnLive}
          onSequenceChange={(sequence) => { setReplayPlaying(false); setReplaySequence(sequence); }}
        />
        <div className="display-controls">
          <label className="replay-speed">REPLAY <select value={replayRate} onChange={(event) => setReplayRate(Number(event.target.value))} aria-label="Replay speed"><option value="1">1×</option><option value="4">4×</option><option value="12">12×</option></select></label>
          <button className="quiet-button" onClick={() => setAnimationPaused((value) => !value)} aria-pressed={animationPaused}>{animationPaused ? "Resume motion" : "Pause motion"}</button>
          <button className="quiet-button" aria-pressed={reducedMotion} onClick={() => setReducedMotion((value) => !value)}>Reduced motion {reducedMotion ? "on" : "off"}</button>
          <button className="quiet-button" aria-pressed={highContrast} onClick={() => setHighContrast((value) => !value)}>Contrast {highContrast ? "high" : "standard"}</button>
          {!showcaseActive && <details className="export-menu">
            <summary>Save / load</summary>
            <div>
              <button disabled={!activeRunId} onClick={() => { if (activeRunId) void downloadExport(activeRunId, "portable"); }}>Save analysis</button>
              <button onClick={() => portableInput.current?.click()}>Load analysis</button>
              <span className="export-menu-label">Other exports</span>
              {["cloudevents", "openlineage", "prov", "obsidian", "reproduction"].map((format) => <button disabled={!activeRunId} onClick={() => { if (activeRunId) void downloadExport(activeRunId, format); }} key={format}>{format}</button>)}
            </div>
          </details>}
          <input
            ref={portableInput}
            hidden
            type="file"
            accept=".evolastra,application/vnd.evolastra.analysis+zip,application/zip"
            onChange={(event) => { const file = event.target.files?.[0]; if (file) void loadPortableAnalysis(file); }}
          />
          {transferStatus && <span className={`transfer-status${transferStatus.error ? " error" : ""}`} role={transferStatus.error ? "alert" : "status"}>{transferStatus.text}</span>}
          {showcaseActive ? <span className="showcase-readonly">PUBLIC SHOWCASE · READ ONLY</span> : <label className="speed-control">SIM <select defaultValue="6" onChange={(event) => { if (activeRunId) void sendCommand(activeRunId, "set_simulator_speed", Number(event.target.value)); }}><option value="1">1×</option><option value="6">6×</option><option value="20">20×</option></select></label>}
        </div>
      </footer>}

      {searchOpen && (
        <div className="search-palette" role="dialog" aria-modal="true" aria-label="Search and command palette">
          <div className="search-box"><span aria-hidden="true">⌕</span><input autoFocus value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search systems, evidence, tools, errors…" aria-label="Search query" /><button className="icon-button" onClick={() => setSearchOpen(false)} aria-label="Close search">×</button></div>
          <div className="search-results">
            {searchQuery.length < 2 ? <p>Type two or more characters. Search keeps entity type and context.</p> : searchResults.length === 0 ? <p>No matching evidence in this run.</p> : searchResults.map((result) => <button key={`${result.entity_type}:${result.id}`} onClick={() => { setSelectedId(result.id); setSearchOpen(false); setView("advanced"); }}><span className="search-kind">{result.entity_type}</span><strong>{result.title}</strong><small>{result.context}</small></button>)}
          </div>
        </div>
      )}
      <ArtifactPreview artifact={artifact} onClose={() => setArtifact(null)} />
      <ConnectionPanel
        open={connectionOpen}
        required={connectionRequired}
        onClose={() => setConnectionOpen(false)}
        onExploreDemo={enterShowcase}
        onConnected={() => {
          setShowcase(null);
          setConnectionRequired(false);
          setConnectionOpen(false);
          setConnectionReady(true);
          setActiveRunId(null);
          void runsQuery.refetch();
        }}
      />
      <Shipyard
        open={shipyardOpen}
        runId={activeRunId}
        preferredBlueprintId={shipyardBlueprintId}
        onClose={() => setShipyardOpen(false)}
        onChanged={() => { void live.refresh(); void runsQuery.refetch(); }}
      />
      <MultiplayerPanel
        open={multiplayerOpen}
        runId={activeRunId}
        state={multiplayer}
        selectedSystem={selectedSystem}
        findings={state?.findings ?? []}
        readOnly={showcaseActive}
        onClose={() => setMultiplayerOpen(false)}
        onChanged={() => { void multiplayerQuery.refetch(); }}
      />
    </div>
  );
}
