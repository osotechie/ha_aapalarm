"""Tests for the integration's declared runtime dependencies."""

import json
from pathlib import Path


def test_manifest_declares_serial_asyncio_dependency():
    """Home Assistant must install serial_asyncio before loading the integration."""
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "aapalarm"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "pyaapalarmmodule==2024.11.24" in manifest["requirements"]
    assert "pyserial-asyncio==0.6" in manifest["requirements"]
