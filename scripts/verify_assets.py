from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    manifest_path = Path("docs/assets/asset-manifest.json")
    if not manifest_path.exists():
        raise SystemExit("Asset manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise SystemExit("Asset manifest must be an object")
    if sys.platform == "win32" and Path("docs/assets/verify-assets.ps1").exists():
        powershell = shutil.which("powershell")
        if powershell is None:
            raise SystemExit("PowerShell is required for asset verification on Windows")
        result = subprocess.run(  # noqa: S603 - fixed local verification command
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "docs/assets/verify-assets.ps1",
            ],
            check=False,
        )
        if result.returncode:
            raise SystemExit(result.returncode)
    else:
        declared = {
            str(item.get("path")) for item in manifest.get("assets", []) if isinstance(item, dict)
        }
        shipped = {
            str(path).replace("\\", "/")
            for root in (Path("apps/web/public"), Path("apps/web/src/assets"))
            if root.exists()
            for path in root.rglob("*")
            if path.is_file()
        }
        missing = shipped - declared
        if missing:
            raise SystemExit(f"Unmanifested assets: {sorted(missing)}")
    print("Asset manifest verification passed.")


if __name__ == "__main__":
    main()
