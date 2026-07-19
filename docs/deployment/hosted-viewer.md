# Static hosted viewer

Evolastra's public deployment is static. The VPS, Netlify site, or CDN serves
HTML, JavaScript, CSS, visual assets, and exactly one curated public showcase at
`/demo/stad-three-empires-v1.json`. It does not run FastAPI, receive Codex
events, accept uploads, store user analysis files, or host a database.

## Data path

```text
Hosted site --serves viewer + one public showcase--> browser
Codex hooks --> local outbox --> local companion --> local SQLite
                                      ^                |
                                      |---- browser ---|
```

The unpaired browser can inspect the read-only showcase entirely in memory. For
real runs, the browser connects directly to `http://127.0.0.1:8000`. Runtime
endpoint validation rejects all non-loopback API origins, and the production CSP
permits same-origin static fetches plus API connections to `127.0.0.1` or
`localhost`.

## Deploy to Netlify

Deploy the repository with the root `netlify.toml`. It builds `apps/web/dist`
and applies the bounded CSP plus frame, referrer, MIME, and permissions headers.
The public showcase is copied into that static output by Vite. Do not add an API
URL, serverless ingestion function, database, proxy rewrite, upload, or second
hosted analysis.

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

They open the hosted viewer and enter the one-time code. Their browser may
request permission to reach a local-network service. Alternatively, they may
choose **Explore public demo** without installing or pairing anything. Every
user-authored Codex session, event, projection, export, and portable analysis
remains under their OS account.

## Privacy boundary

The hosted server receives ordinary static-asset requests, including the public
showcase request, and may log IP address, user agent, requested paths, and
timestamps. The viewer sends no user analysis data to that server. As with any
hosted web application, the operator could later replace the JavaScript, so
users must trust the deployment operator or verify/self-host a reviewed build.

The [ARCH-008 invariant](../architecture/invariants.md) and security scan allow
only the versioned aggregate showcase. Its content is display-oriented public
data with synthetic IDs, bounded figure rows, and explicit validation caveats;
it is not a portable export of a private run.
