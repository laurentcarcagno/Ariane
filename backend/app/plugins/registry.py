"""Plugin discovery: every ``plugins/<dir>/manifest.json`` with a ``plugin.py`` exposing ``parse``."""
from __future__ import annotations

import importlib
import json
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType

PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins"
if str(PLUGINS_DIR.parent) not in sys.path:  # plugins are importable as ``plugins.<name>``
    sys.path.insert(0, str(PLUGINS_DIR.parent))


@lru_cache
def discover() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for manifest in sorted(PLUGINS_DIR.glob("*/manifest.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["module"] = f"plugins.{manifest.parent.name}.plugin"
        found[data["id"]] = data
    return found


def load(plugin_id: str) -> ModuleType:
    info = discover().get(plugin_id)
    if info is None:
        raise KeyError(plugin_id)
    return importlib.import_module(info["module"])
