# Static hosted viewer

The public deployment contains only the compiled files from `apps/web/dist`. Do not deploy FastAPI, SQLite, an ingestion endpoint, a database, or a Codex connector on the VPS.

Build and copy the viewer:

```bash
npm --prefix apps/web ci
npm --prefix apps/web run build
sudo mkdir -p /srv/evolastra-viewer
sudo cp -R apps/web/dist/. /srv/evolastra-viewer/
```

Use `Caddyfile.example` or `netlify.toml` to serve the directory with the restrictive local-companion CSP. Each user separately installs the companion on their own computer and allowlists the exact viewer origin.
