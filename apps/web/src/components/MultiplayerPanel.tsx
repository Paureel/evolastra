import { useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  claimMultiplayerSystem,
  fetchMultiplayerReadiness,
  hostMultiplayer,
  joinMultiplayer,
  leaveMultiplayer,
  publishMultiplayerFinding,
  releaseMultiplayerSystem,
  renewMultiplayerInvite,
} from "../api";
import type { Entity, MultiplayerReadiness, MultiplayerState } from "../types";

interface MultiplayerPanelProps {
  open: boolean;
  runId: string | null;
  state: MultiplayerState;
  selectedSystem: { id: string; title: string } | null;
  findings: Entity[];
  readOnly?: boolean;
  onClose: () => void;
  onChanged: (state?: MultiplayerState) => void;
}

const PLAYER_COLORS = ["#71E6E1", "#FFD36A", "#B98BEA", "#FF716C", "#7EDB83", "#73A7FF"];

export function MultiplayerPanel({ open, runId, state, selectedSystem, findings, readOnly = false, onClose, onChanged }: MultiplayerPanelProps) {
  const [entryMode, setEntryMode] = useState<"host" | "join">("host");
  const [displayName, setDisplayName] = useState("");
  const [color, setColor] = useState(PLAYER_COLORS[0]);
  const [shareUrl, setShareUrl] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [findingId, setFindingId] = useState("");
  const [readiness, setReadiness] = useState<MultiplayerReadiness | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open || readOnly) return;
    setError(null);
    void fetchMultiplayerReadiness().then((result) => {
      setReadiness(result);
      setShareUrl((current) => current || result.suggested_share_url || "");
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Tailscale readiness could not be checked"));
  }, [open, readOnly]);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [busy, onClose, open]);

  const localPlayer = state.players?.find((player) => player.id === state.session?.local_player_id);
  const selectedClaim = state.claims?.find((claim) => claim.node_id === selectedSystem?.id);
  const claimOwner = state.players?.find((player) => player.id === selectedClaim?.player_id);
  const publicationPlayers = useMemo(() => new Map((state.players ?? []).map((player) => [player.id, player])), [state.players]);

  if (!open) return null;

  const host = async () => {
    if (!runId || displayName.trim().length < 2 || !shareUrl.trim()) return;
    setBusy("host"); setError(null);
    try {
      const result = await hostMultiplayer(runId, displayName.trim(), color, shareUrl.trim());
      setInviteCode(result.invite_code);
      onChanged(result.state);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The multiplayer session could not be hosted");
    } finally { setBusy(null); }
  };

  const join = async () => {
    if (displayName.trim().length < 2 || joinCode.trim().length < 40) return;
    setBusy("join"); setError(null);
    try {
      const result = await joinMultiplayer(joinCode.trim(), displayName.trim(), color);
      onChanged(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The multiplayer session could not be joined");
    } finally { setBusy(null); }
  };

  const renewInvite = async () => {
    if (!runId) return;
    setBusy("invite"); setError(null);
    try {
      const result = await renewMultiplayerInvite(runId);
      setInviteCode(result.invite_code); setCopied(false);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "A fresh invite could not be created"); }
    finally { setBusy(null); }
  };

  const changeClaim = async () => {
    if (readOnly || !runId || !selectedSystem) return;
    setBusy("claim"); setError(null);
    try {
      const result = selectedClaim?.player_id === localPlayer?.id
        ? await releaseMultiplayerSystem(runId, selectedSystem.id)
        : await claimMultiplayerSystem(runId, selectedSystem.id);
      onChanged(result);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The system claim could not be changed"); }
    finally { setBusy(null); }
  };

  const publish = async () => {
    if (readOnly || !runId || !findingId) return;
    setBusy("publish"); setError(null);
    try { const result = await publishMultiplayerFinding(runId, findingId); onChanged(result); setFindingId(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The finding could not be published"); }
    finally { setBusy(null); }
  };

  const leave = async () => {
    if (readOnly || !runId) return;
    setBusy("leave"); setError(null);
    try { await leaveMultiplayer(runId); setInviteCode(""); onChanged({ enabled: false }); onClose(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The multiplayer session could not be closed"); }
    finally { setBusy(null); }
  };

  return <div className="federation-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <section className="federation-panel" role="dialog" aria-modal="true" aria-labelledby="federation-title">
      <header className="federation-head">
        <div className="federation-emblem" aria-hidden="true"><i /><i /><i /></div>
        <div><span className="eyebrow">{readOnly ? "PUBLIC SHOWCASE · READ ONLY" : "COOPERATIVE RESEARCH NETWORK"}</span><h2 id="federation-title">{readOnly ? "Three-empire expedition" : "Research federation"}</h2><p>{readOnly ? "Inspect how three research directions divide the scientific frontier." : "Divide the problem into territories. Share conclusions, not private workspaces."}</p></div>
        <button className="icon-button" onClick={onClose} disabled={Boolean(busy)} aria-label="Close multiplayer" autoFocus>×</button>
      </header>

      {!state.enabled ? <div className="federation-entry">
        <div className="federation-entry-tabs" role="tablist" aria-label="Multiplayer setup">
          <button role="tab" aria-selected={entryMode === "host"} className={entryMode === "host" ? "active" : ""} onClick={() => setEntryMode("host")}>Host project</button>
          <button role="tab" aria-selected={entryMode === "join"} className={entryMode === "join" ? "active" : ""} onClick={() => setEntryMode("join")}>Join project</button>
        </div>
        <div className="federation-route" aria-label="Private multiplayer route"><span>THIS DEVICE</span><i /><span>TAILSCALE</span><i /><span>HOST DEVICE</span></div>
        <label className="federation-field">Player name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={80} placeholder="Researcher name" /></label>
        <fieldset className="federation-colors"><legend>Territory color</legend>{PLAYER_COLORS.map((item) => <button type="button" aria-label={`Use territory color ${item}`} aria-pressed={color === item} key={item} style={{ "--player-color": item } as CSSProperties} onClick={() => setColor(item)} />)}</fieldset>
        {entryMode === "host" ? <>
          <label className="federation-field">Tailscale Serve URL<input value={shareUrl} onChange={(event) => setShareUrl(event.target.value)} placeholder="https://device.tailnet-name.ts.net" /></label>
          <div className="federation-command"><span>{readiness?.tailscale_installed ? "Expose the paired companion to your tailnet" : "Install and sign in to Tailscale, then run"}</span><code>{readiness?.serve_command ?? "tailscale serve --bg http://127.0.0.1:8000"}</code></div>
          <button className="primary-button" onClick={() => void host()} disabled={Boolean(busy) || displayName.trim().length < 2 || !shareUrl.trim()}>{busy === "host" ? "Opening federation…" : "Host this project"}</button>
        </> : <>
          <label className="federation-field">Invite code<textarea value={joinCode} onChange={(event) => setJoinCode(event.target.value)} placeholder="Paste the EVO1 invite from the host" /></label>
          <p className="federation-note">Load the matching <code>.evolastra</code> analysis on this device before joining. The invite carries no project content.</p>
          <button className="primary-button" onClick={() => void join()} disabled={Boolean(busy) || displayName.trim().length < 2 || joinCode.trim().length < 40}>{busy === "join" ? "Joining host…" : "Join federation"}</button>
        </>}
        <p className="federation-note">Netlify remains a static viewer and stores no project or multiplayer data.</p>
      </div> : <div className="federation-console">
        <div className={`federation-state ${state.session?.status ?? "paused"}`}><span><i />{state.session?.status === "active" ? state.session.simulation_active ? "Three-empire simulation active" : "Federation online" : state.session?.status === "closed" ? "Host closed session" : "Host unreachable — session paused"}</span><small>{readOnly ? "CURATED PUBLIC RESULTS" : state.session?.simulation_active ? "SYNTHETIC PLAYERS · LOCAL DATA" : state.session?.mode === "host" ? "YOU ARE HOST" : "JOINED THROUGH TAILSCALE"}</small></div>
        <div className="federation-grid">
          <section aria-labelledby="members-title"><div className="federation-section-head"><span>FEDERATION ROSTER</span><h3 id="members-title">Researchers</h3></div>
            <div className="federation-roster">{(state.players ?? []).map((player) => <div className={player.online ? "online" : "offline"} key={player.id}><i style={{ background: player.color, boxShadow: `0 0 9px ${player.color}` }} /><span><strong>{player.display_name}{!readOnly && player.id === localPlayer?.id ? " · you" : ""}</strong><small>{player.role} · {player.online ? "online" : "away"}</small></span><b>{(state.claims ?? []).filter((claim) => claim.player_id === player.id).length}</b></div>)}</div>
            {!readOnly && state.session?.mode === "host" && <div className="federation-invite"><button className="quiet-button" onClick={() => void renewInvite()} disabled={Boolean(busy)}>{inviteCode ? "Rotate invite" : "Create invite"}</button>{inviteCode && <><textarea readOnly value={inviteCode} aria-label="Multiplayer invite code" /><button className="primary-button" onClick={() => void navigator.clipboard.writeText(inviteCode).then(() => setCopied(true))}>{copied ? "Copied" : "Copy invite"}</button></>}</div>}
          </section>
          <section aria-labelledby="territory-title"><div className="federation-section-head"><span>ACTIVE FRONT</span><h3 id="territory-title">Territory and discoveries</h3></div>
            <div className="territory-order"><small>SELECTED SYSTEM</small><strong>{selectedSystem?.title ?? "Select a system on the map"}</strong>{selectedSystem && <><span>{claimOwner ? `Claimed by ${claimOwner.display_name}` : "Unclaimed direction"}</span>{!readOnly && <button className="primary-button" onClick={() => void changeClaim()} disabled={Boolean(busy) || Boolean(selectedClaim && selectedClaim.player_id !== localPlayer?.id)}>{selectedClaim?.player_id === localPlayer?.id ? "Release system" : selectedClaim ? "Occupied" : "Claim system"}</button>}</>}</div>
            {!readOnly && <div className="publish-order"><label>Publish a local finding<select value={findingId} onChange={(event) => setFindingId(event.target.value)}><option value="">Choose a finding</option>{findings.map((finding) => <option key={finding.id} value={finding.id}>{String(finding.title ?? finding.statement ?? finding.id)}</option>)}</select></label><button className="quiet-button" disabled={!findingId || Boolean(busy)} onClick={() => void publish()}>Publish summary</button><small>Only the bounded title and summary cross the tailnet.</small></div>}
            <div className="federation-publications">{(state.publications ?? []).length === 0 ? <p>No discoveries published yet.</p> : (state.publications ?? []).map((publication) => <article key={publication.id}><i style={{ background: publicationPlayers.get(publication.player_id)?.color }} /><div><strong>{publication.title}</strong><p>{publication.summary}</p><small>{publicationPlayers.get(publication.player_id)?.display_name ?? "Researcher"}</small></div></article>)}</div>
          </section>
        </div>
        {state.connection_error && <p className="federation-error" role="alert">{state.connection_error}</p>}
        <footer className="federation-foot"><span>{readOnly ? "This one aggregate showcase is public; user projects remain on participant devices." : "Project data remains on participant devices. Netlify stores nothing."}</span>{readOnly ? <button className="quiet-button" onClick={onClose}>Close showcase details</button> : <button className="danger-button" onClick={() => void leave()} disabled={Boolean(busy)}>{state.session?.mode === "host" ? state.session.status === "closed" ? "Reset to single player" : "Close federation" : "Leave session"}</button>}</footer>
      </div>}
      {error && <p className="federation-error" role="alert">{error}</p>}
    </section>
  </div>;
}
