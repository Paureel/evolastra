# Multiplayer federation

_Explore one underlying project from several locally operated observatories_

---

Phase 1 multiplayer adds a Stellaris-style collaboration overlay without moving
the underlying analysis to Netlify or another application server. One player is
the host. Every player keeps their own companion, Codex installation, prompts,
datasets, artifacts, and project copy on their own computer.

## 🧭 What multiplayer shares

| Shared with the host | Kept on each player's device |
| --- | --- |
| Display name and territory color | Codex credentials and conversations |
| Online/away presence | Raw prompts and agent telemetry |
| Claimed analysis-system IDs | Datasets and filesystem paths |
| Finding titles and summaries selected with **Publish summary** | Artifacts and unselected findings |
| Non-secret project fingerprint | Complete event history and exports |

The collaboration overlay is separate from the durable semantic event log.
Claims and presence never change replay or single-player exports.

## 🛠️ Prerequisites

Every participant needs:

- Evolastra installed with the Local Private companion running
- Tailscale installed and signed in
- Membership in the same private tailnet
- The same `.evolastra` analysis loaded locally

The Netlify site may still serve the interface. It receives only ordinary static
asset requests and never receives multiplayer or project content.

## 🛰️ Host a project

1. Load the project you want to share.
2. Expose only the federation path from PowerShell:

   ```powershell
   tailscale serve --bg --set-path /api/v1/federation http://127.0.0.1:8000/api/v1/federation
   ```

3. Select **Single player** in the top command bar.
4. Choose **Host project**, enter a player name and territory color, and use the
   HTTPS `.ts.net` address for this device.
5. Select **Host this project**, then **Create invite**.
6. Send the `EVO1…` invite through a private channel to the intended players.

Invites expire after 24 hours. **Rotate invite** invalidates the previous invite
for new joins; existing members keep their scoped session grants.

Never use Tailscale Funnel for Evolastra. Funnel makes a service public, while
Phase 1 is designed for a private tailnet of known collaborators.

## 🤝 Join a project

1. Obtain the same project as a `.evolastra` file through your normal trusted
   file-sharing method and load it in your local Evolastra first.
2. Select **Single player → Join project**.
3. Enter your player name, choose an unused territory color, and paste the invite.
4. Select **Join federation**.

Evolastra compares a non-secret fingerprint derived from the run identity and
seed. A mismatch stops the join rather than silently showing claims on the wrong
project. The invite itself does not contain project data.

The member grant exists only in companion memory. Restarting a guest companion
pauses its federation view; obtain a fresh invite and rejoin. This avoids writing
a reusable multiplayer credential to disk.

## 🪐 Claim systems

1. Select an analysis star in the Galaxy Map.
2. Open the federation panel from the top command bar.
3. Select **Claim system**.

The map adds a colored territorial ring without replacing its ordinary status
color or shape. One player can own a system at a time in Phase 1. The owner can
select **Release system**; transfers are performed by release followed by claim.

Each player's ships still launch through their own local Codex. Territory is a
coordination signal, not remote control over another person's agents.

## 📡 Publish a discovery

In the federation panel, choose a local finding and select **Publish summary**.
Only its bounded title and summary cross the tailnet. Evidence artifacts, raw
content, prompts, and the rest of the local finding object remain private.

Published summaries appear in the federation chart with the author's color.
They do not become canonical findings in another player's project automatically;
promotion into the analytical record remains an explicit local decision.

## ⏸️ Host loss and shutdown

When the host cannot be reached, guest panels display **Host unreachable —
session paused**. The last known colors, claims, and publications remain visible,
but guest mutations stop. Phase 1 has no host migration.

The host selects **Close federation** to tell connected members the session is
closed, then **Reset to single player** to remove the local overlay. Stop the
tailnet route when it is no longer needed:

```powershell
tailscale serve reset
```

Closing multiplayer does not delete or modify the underlying analysis. Deleting
the analysis does remove its local multiplayer overlay.

## Phase 1 limits

- A federation supports up to 24 players, including the host.
- The shared publication chart retains up to 500 explicitly published summaries.
- The host is authoritative and must remain online; Phase 1 has no host migration.
- Players can leave and release their own claims. The host can rotate invites or
  close the federation, but there is no per-member removal interface yet.
- Project files, chat, artifacts, and raw evidence are not synchronized.
- If a guest companion restarts, its in-memory member grant is gone. Rejoin with
  a current invite; using the same name and color reconnects the offline identity.

These limits bound the local host's storage and abuse surface. They are product
constraints, not recommendations to expose the companion publicly.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Multiplayer says Local Private is required | Install and start the companion instead of using the development server. |
| Tailscale is not ready | Run `tailscale status`, confirm both devices are in the same tailnet, and recreate the path-only Serve route. |
| Invite is rejected | Ask the host to rotate the expired invite and confirm you loaded the same `.evolastra` analysis. |
| Name or color is already in use | Choose a unique identity, or reuse both your previous name and color after that identity becomes offline. |
| Host is unreachable | Keep the paused view open, restore the host and its Serve route, then retry; no mutations occur while paused. |
| Single player is desired | Leave or close the federation and select **Reset to single player**; the underlying analysis is unchanged. |

## 🔐 Security boundary

- The companion continues listening on loopback only.
- Tailscale Serve exposes only `/api/v1/federation`.
- Federation requests require a Tailscale identity header and a scoped invite or
  member capability.
- Those capabilities cannot read runs, events, artifacts, exports, pairing state,
  Codex missions, or the companion root capability.
- Netlify stores no project or session data.

This is private collaboration among tailnet members, not an internet-facing,
anonymous, or multi-tenant service.
