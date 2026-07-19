from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_repository_uses_unmodified_mit_grant_and_disclaimer() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    normalized = " ".join(license_text.split())

    assert license_text.startswith("MIT License\n\nCopyright (c) 2026 Paureel")
    assert "Permission is hereby granted, free of charge" in license_text
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in license_text
    assert "IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE" in normalized


def test_javascript_manifests_declare_mit() -> None:
    for manifest in (ROOT / "package.json", ROOT / "apps" / "web" / "package.json"):
        assert json.loads(manifest.read_text(encoding="utf-8"))["license"] == "MIT"
