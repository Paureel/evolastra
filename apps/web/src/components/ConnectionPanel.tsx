import { useEffect, useState } from "react";
import { currentEndpoint, pairCompanion } from "../api";

interface ConnectionPanelProps {
  open: boolean;
  required: boolean;
  onClose: () => void;
  onConnected: () => void;
  onExploreDemo: () => Promise<void>;
}

export function ConnectionPanel({ open, required, onClose, onConnected, onExploreDemo }: ConnectionPanelProps) {
  const [endpoint, setEndpoint] = useState(currentEndpoint());
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  useEffect(() => {
    if (open) setEndpoint(currentEndpoint());
  }, [open]);

  if (!open) return null;
  const connect = async () => {
    setConnecting(true);
    setError(null);
    try {
      await pairCompanion(endpoint, code);
      setCode("");
      onConnected();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Pairing failed");
    } finally {
      setConnecting(false);
    }
  };
  const exploreDemo = async () => {
    setDemoLoading(true);
    setError(null);
    try {
      await onExploreDemo();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The public showcase could not be loaded");
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="connection-backdrop" role="presentation">
      <section className="connection-panel" role="dialog" aria-modal="true" aria-labelledby="connection-title">
        <div className="connection-orbit" aria-hidden="true"><i /><i /></div>
        <span className="eyebrow">CHOOSE AN OBSERVATORY MODE</span>
        <h2 id="connection-title">Enter Evolastra</h2>
        <div className="showcase-launch">
          <span className="showcase-empires" aria-hidden="true"><i /><i /><i /></span>
          <div><small>NO PAIRING REQUIRED · READ ONLY</small><h3>Three-empire STAD expedition</h3><p><strong>STAD: Stomach Adenocarcinoma.</strong> Explore a twelve-phase Copy Number Alteration (CNA) analysis with six hypotheses, aggregate figures, and three expanding empires.</p></div>
          <button className="showcase-button" disabled={demoLoading || connecting} onClick={() => void exploreDemo()}>{demoLoading ? "Loading expedition…" : "Explore public demo"}</button>
        </div>
        <div className="connection-divider"><span>OR CONNECT LOCAL CODEX</span></div>
        <p>The hosted site contains viewer code and one curated public showcase. Your Codex events, analysis database, exports, and access token stay on this computer.</p>
        <div className="privacy-route" aria-label="Private data route">
          <span>CODEX</span><i /><span>THIS DEVICE</span><i /><span>BROWSER</span>
        </div>
        <label className="connection-field">
          <span>One-time pairing code</span>
          <input autoFocus value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} placeholder="A1B2-C3D4-E5F6" autoComplete="off" spellCheck={false} />
          <small>Run <code>evolastra pair</code> on this computer to create a five-minute code.</small>
        </label>
        <details className="connection-endpoint">
          <summary>Local companion address</summary>
          <label><span>Loopback address</span><input value={endpoint} onChange={(event) => setEndpoint(event.target.value)} spellCheck={false} /></label>
          <small>Only localhost and loopback addresses are accepted.</small>
        </details>
        {error && <p className="connection-error" role="alert">{error}</p>}
        <div className="connection-actions">
          {!required && <button className="quiet-button" onClick={onClose}>Cancel</button>}
          <button className="primary-button" disabled={connecting || code.trim().length < 14} onClick={() => void connect()}>{connecting ? "Connecting…" : "Connect observatory"}</button>
        </div>
        <small className="connection-storage">Session access is kept in this browser tab and expires automatically.</small>
      </section>
    </div>
  );
}
