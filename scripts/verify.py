from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

FAST_COMMANDS = [
    [sys.executable, "scripts/harness.py", "check"],
    [sys.executable, "-m", "ruff", "check", "."],
    [sys.executable, "-m", "mypy", "apps/api"],
    [sys.executable, "-m", "pytest"],
    ["npm", "--prefix", "apps/web", "run", "typecheck"],
    ["npm", "--prefix", "apps/web", "run", "test"],
]

RELEASE_COMMANDS = [
    *FAST_COMMANDS[:4],
    [sys.executable, "-m", "asterism_api.cli", "migrate"],
    *FAST_COMMANDS[4:],
    ["npm", "--prefix", "apps/web", "run", "build"],
    ["npm", "--prefix", "apps/web", "audit", "--audit-level=moderate"],
    ["npm", "--prefix", "apps/web", "run", "test:e2e"],
    [sys.executable, "scripts/verify_assets.py"],
    [sys.executable, "scripts/security_scan.py"],
    [sys.executable, "-m", "pip_audit", "-r", "requirements.lock"],
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Evolastra verification")
    parser.add_argument("--fast", action="store_true", help="skip build, browser, asset, and audit gates")
    args = parser.parse_args()
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm is required")
    commands = FAST_COMMANDS if args.fast else RELEASE_COMMANDS
    for command in commands:
        if command[0] == "npm":
            command = [npm, *command[1:]]
        print(f"\n> {' '.join(command)}", flush=True)
        result = subprocess.run(command, check=False)  # noqa: S603
        if result.returncode:
            raise SystemExit(result.returncode)
    label = "Fast repository preflight" if args.fast else "Practical release gate"
    print(f"\n{label} passed.")


if __name__ == "__main__":
    main()
