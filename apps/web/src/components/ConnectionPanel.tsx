import { useEffect, useState } from "react";
import { currentEndpoint, pairCompanion } from "../api";

export const HOSTED_VIEWER_ORIGIN = "https://evolastra.netlify.app";
export const HUMAN_INSTALL_COMMAND = `git clone https://github.com/Paureel/evolastra.git
Set-Location evolastra
powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\bootstrap.ps1 -NoBrowser -Origin ${HOSTED_VIEWER_ORIGIN}`;
export const AGENT_SETUP_PROMPT = `Set up Evolastra on this Windows computer and connect it to ${HOSTED_VIEWER_ORIGIN}.
If there is no checkout, clone https://github.com/Paureel/evolastra.git first. Read AGENTS.md and docs/getting-started.md completely. Run npm run bootstrap:check, then run powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\bootstrap.ps1 -NoBrowser -Origin ${HOSTED_VIEWER_ORIGIN}. Verify the companion and Codex hook status. Preserve the local-private boundary and never read or print ~/.evolastra/companion-token.
Then stop and tell me to restart Codex, open /hooks, review the Evolastra commands, and approve them. Only when I confirm this browser's pairing screen is open, run & .\\.venv\\Scripts\\evolastra.exe pair once and ask me to enter the five-minute code.`;

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
  const [setupAudience, setSetupAudience] = useState<"human" | "agent">("human");
  const [copied, setCopied] = useState<"human" | "agent" | null>(null);

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
  const copySetup = async (kind: "human" | "agent", value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
      window.setTimeout(() => setCopied((current) => current === kind ? null : current), 2_000);
    } catch {
      setError("Copy is unavailable in this browser. Select the displayed instructions manually.");
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
        <p><strong>Yes, first-time setup installs a small local companion and Codex hooks.</strong> The hosted site cannot inspect Codex by itself. Your events, analysis database, exports, and access token stay on this computer.</p>
        <div className="privacy-route" aria-label="Private data route">
          <span>CODEX</span><i /><span>THIS DEVICE</span><i /><span>BROWSER</span>
        </div>
        <section className="connection-setup" aria-labelledby="setup-title">
          <header><div><small>INSTALL ONCE · PAIR EACH BROWSER TAB</small><h3 id="setup-title">Connect your Codex</h3></div><a href="https://github.com/Paureel/evolastra/blob/main/docs/getting-started.md" target="_blank" rel="noreferrer">Full guide ↗</a></header>
          <div className="setup-tabs" role="tablist" aria-label="Connection setup audience">
            <button role="tab" aria-selected={setupAudience === "human"} onClick={() => setSetupAudience("human")}>For humans</button>
            <button role="tab" aria-selected={setupAudience === "agent"} onClick={() => setSetupAudience("agent")}>For Codex agents</button>
          </div>
          {setupAudience === "human" ? <div className="setup-panel" role="tabpanel" aria-label="For humans">
            <p>Requires Windows 10+, Git, Python 3.12+, Node.js 20+, and Codex desktop.</p>
            <ol>
              <li><span>1</span><div><strong>Install the local bridge</strong><small>Open PowerShell and run the public-repository setup below.</small></div></li>
              <li><span>2</span><div><strong>Restart Codex once</strong><small>Open <code>/hooks</code>, review the Evolastra commands, and approve them.</small></div></li>
              <li><span>3</span><div><strong>Pair this tab</strong><small>From the checkout run <code>&amp; .\.venv\Scripts\evolastra.exe pair</code>, then enter the code below.</small></div></li>
            </ol>
            <div className="setup-command"><code>{HUMAN_INSTALL_COMMAND}</code><button onClick={() => void copySetup("human", HUMAN_INSTALL_COMMAND)}>{copied === "human" ? "Copied" : "Copy install commands"}</button></div>
          </div> : <div className="setup-panel agent-setup-panel" role="tabpanel" aria-label="For Codex agents">
            <p>Give your Codex agent this bounded setup task. It installs and verifies everything it safely can, then pauses for your hook approval and pairing code.</p>
            <blockquote>{AGENT_SETUP_PROMPT}</blockquote>
            <div className="agent-setup-actions">
              <button className="setup-copy-button" onClick={() => void copySetup("agent", AGENT_SETUP_PROMPT)}>{copied === "agent" ? "Prompt copied" : "Copy agent setup prompt"}</button>
              <a href="/agent-setup.md" target="_blank" rel="noreferrer">Agent setup file ↗</a>
              <a href="/llms.txt" target="_blank" rel="noreferrer">llms.txt ↗</a>
              <a href="https://github.com/Paureel/evolastra/blob/main/AGENTS.md" target="_blank" rel="noreferrer">AGENTS.md ↗</a>
            </div>
          </div>}
        </section>
        <label className="connection-field">
          <span>One-time pairing code</span>
          <input value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} placeholder="A1B2-C3D4-E5F6" autoComplete="off" spellCheck={false} />
          <small>From the checkout, run <code>&amp; .\.venv\Scripts\evolastra.exe pair</code> to create a five-minute code.</small>
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
