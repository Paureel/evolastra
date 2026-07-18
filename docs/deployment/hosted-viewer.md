# Static hosted viewer

Evolastra's public deployment is a static viewer only. The VPS, Netlify site, or CDN serves HTML, JavaScript, CSS, and the favicon. It does not run FastAPI, receive Codex events, store analysis files, or host a database.

## Data path

```text
Hosted site --serves static code--> browser
Codex hooks --> local outbox --> local companion --> local SQLite
                                      ^                |
                                      |---- browser ---|
```

The browser connects directly to `http://127.0.0.1:8000`. Runtime endpoint validation rejects all non-loopback API origins, and the production CSP permits API connections only to `127.0.0.1` or `localhost`.

## Deploy to Netlify

Deploy the repository with the root `netlify.toml`. It builds `apps/web/dist` and applies the local-only CSP plus frame, referrer, MIME, and permissions headers. Do not add an API URL, serverless ingestion function, database, or proxy rewrite.

## Deploy to a VPS

Build and copy only the static output:

```bash
npm --prefix apps/web ci
npm --prefix apps/web run build
sudo mkdir -p /srv/evolastra-viewer
sudo cp -R apps/web/dist/. /srv/evolastra-viewer/
```

Serve it with `deploy/Caddyfile.example`. Do not install the Python backend or database on the VPS.

## User setup

Each user runs this on their own computer, using the exact hosted viewer origin:

```powershell
evolastra service install --origin https://viewer.example.com
evolastra service start
evolastra pair
```

They open the hosted viewer and enter the one-time code. Their browser may request permission to reach a local-network service. Every Codex session, event, projection, export, and portable analysis remains under their OS account.

## Privacy boundary

The hosted server receives ordinary static-asset requests and may log IP address, user agent, requested paths, and timestamps. The current viewer sends no analysis data to that server. As with any hosted web application, the operator could later replace the JavaScript, so users must trust the deployment operator or verify/self-host a reviewed build.
