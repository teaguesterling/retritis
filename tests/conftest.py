"""Shared test helpers: load repo scripts/hooks as modules by path."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_module(relpath: str, name: str):
    """Import a repo file (scripts/, hooks/) that isn't on sys.path."""
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
