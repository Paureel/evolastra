from __future__ import annotations

import shutil
import subprocess
import sys

COMMANDS = [
    [sys.executable, "-m", "ruff", "check", "."],
    [sys.executable, "-m", "mypy", "apps/api"],
    [sys.executable, "-m", "pytest"],
    [sys.executable, "-m", "asterism_api.cli", "migrate"],
    ["npm", "--prefix", "apps/web", "run", "typecheck"],
    ["npm", "--prefix", "apps/web", "run", "test"],
    ["npm", "--prefix", "apps/web", "run", "build"],
    ["npm", "--prefix", "apps/web", "audit", "--audit-level=moderate"],
    ["npm", "--prefix", "apps/web", "run", "test:e2e"],
    [sys.executable, "scripts/verify_assets.py"],
    [sys.executable, "scripts/security_scan.py"],
    [sys.executable, "-m", "pip_audit", "-r", "requirements.lock"],
]


def main() -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm is required")
    for command in COMMANDS:
        if command[0] == "npm":
            command = [npm, *command[1:]]
        print(f"\n> {' '.join(command)}", flush=True)
        result = subprocess.run(command, check=False)  # noqa: S603
        if result.returncode:
            raise SystemExit(result.returncode)
    print("\nPractical release gate passed.")


if __name__ == "__main__":
    main()
