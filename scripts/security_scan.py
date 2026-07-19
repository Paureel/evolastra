from __future__ import annotations

import re
from pathlib import Path

PATTERNS = {
    "dynamic-code": re.compile(r"\b(eval|exec)\s*\(|new\s+Function\s*\("),
    "unsafe-html": re.compile(r"dangerouslySetInnerHTML|\.innerHTML\s*=|insertAdjacentHTML"),
    "shell-execution": re.compile(r"shell\s*=\s*True|os\.system\s*\("),
    "wildcard-cors": re.compile(r"allow_origins\s*=\s*\[\s*[\"']\*[\"']"),
    "secret-material": re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|BEGIN [A-Z ]+PRIVATE KEY)"),
}


def main() -> None:
    findings: list[str] = []
    roots = [Path("apps/api"), Path("apps/web/src"), Path("apps/web/public/demo"), Path("integrations"), Path("sdk")]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {
                ".py",
                ".ts",
                ".tsx",
                ".js",
                ".json",
            }:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for name, pattern in PATTERNS.items():
                if pattern.search(text):
                    findings.append(f"{name}: {path}")

    # The public deployment is a static viewer plus one allowlisted aggregate
    # showcase. Keep this boundary machine-checkable so a remote API/connector
    # or second hosted analysis cannot quietly return later.
    forbidden_paths = [
        Path("apps/api/asterism_api/connector.py"),
        Path("deploy/evolastra.env.example"),
        Path("deploy/evolastra.service"),
    ]
    for path in forbidden_paths:
        if path.exists():
            findings.append(f"remote-storage-component: {path}")

    web_source = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in Path("apps/web/src").rglob("*")
        if path.is_file() and path.suffix.lower() in {".ts", ".tsx", ".js"}
    )
    for marker in ("VITE_API_URL", "connectWithAccessToken"):
        if marker in web_source:
            findings.append(f"remote-api-client: apps/web/src contains {marker}")

    caddy = Path("deploy/Caddyfile.example").read_text(encoding="utf-8")
    if "reverse_proxy" in caddy:
        findings.append("remote-api-proxy: deploy/Caddyfile.example")

    netlify = Path("netlify.toml").read_text(encoding="utf-8")
    csp = next((line for line in netlify.splitlines() if "connect-src" in line), "")
    if "connect-src https:" in csp:
        findings.append("remote-connect-csp: netlify.toml")
    if "connect-src 'self'" not in csp:
        findings.append("missing-static-showcase-csp: netlify.toml")
    if "http://127.0.0.1:*" not in csp or "http://localhost:*" not in csp:
        findings.append("missing-loopback-csp: netlify.toml")
    if findings:
        raise SystemExit("Security scan failed:\n" + "\n".join(findings))
    print("Focused source security scan passed.")


if __name__ == "__main__":
    main()
