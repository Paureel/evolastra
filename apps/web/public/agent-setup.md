# Connect Codex to Evolastra

This page is the machine-readable setup path for the hosted Evolastra viewer at
https://evolastra.netlify.app.

## Objective

Install Evolastra's local companion and managed Codex hooks on the user's
Windows computer, allow the hosted viewer origin, and prepare one-time browser
pairing without moving analysis data to Netlify.

## Instructions for a coding agent

1. If there is no checkout, clone the public repository:

   ```powershell
   git clone https://github.com/Paureel/evolastra.git
   Set-Location evolastra
   ```

2. Read `AGENTS.md` and `docs/getting-started.md` completely. Follow the nearest
   nested `AGENTS.md` for every file you touch.
3. Run the prerequisite check:

   ```powershell
   npm run bootstrap:check
   ```

4. On a supported Windows computer, install for the hosted viewer without
   opening another browser window:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -NoBrowser -Origin https://evolastra.netlify.app
   ```

5. Verify both local components:

   ```powershell
   & .\.venv\Scripts\evolastra.exe service status
   & .\.venv\Scripts\evolastra.exe codex status
   ```

6. Never read, print, copy, or expose `~/.evolastra/companion-token`. Preserve
   the local-private boundary and do not upload the database, outbox, artifacts,
   pairing state, credentials, or user datasets.
7. Stop and tell the user to restart Codex once, open `/hooks`, review the
   Evolastra commands, and approve them. This human trust action cannot be
   automated safely.
8. Only after the user says the hosted pairing screen is open, generate one
   five-minute code:

   ```powershell
   & .\.venv\Scripts\evolastra.exe pair
   ```

   Ask the user to enter that code at https://evolastra.netlify.app. Do not
   repeatedly generate codes.

9. If the hosted viewer reports `Failed to fetch`, do not weaken the loopback
   binding or expose user data. Verify `evolastra service status`, then ask the
   user to open the site in ordinary Chrome and allow local/loopback network
   access for the Netlify origin. The Codex in-app browser may not expose this
   permission. If the local viewer works, direct the user to the clean-profile
   fallback in `docs/getting-started.md#hosted-viewer-says-failed-to-fetch`.

## Expected architecture

Codex hooks write redacted events to a local outbox. The local companion stores
the event log, semantic projection, artifacts, and pairing authority on the
user's computer. The hosted site is a static viewer that connects from the
browser directly to the loopback companion. Netlify does not receive the user's
analysis data.

## Authoritative references

- Repository contract: https://github.com/Paureel/evolastra/blob/main/AGENTS.md
- Getting started: https://github.com/Paureel/evolastra/blob/main/docs/getting-started.md
- Privacy model: https://github.com/Paureel/evolastra/blob/main/docs/security/privacy-model.md
- Local operations: https://github.com/Paureel/evolastra/blob/main/docs/deployment/local-private.md
