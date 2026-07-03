#!/usr/bin/env python3
"""verify_plugins — pinned, verified plugin marketplace (fail closed).

`/plugin marketplace add teaguesterling/retritis` trusts whatever is at HEAD
of a mutable repo. This tool replaces that trust-on-first-use with
verify-then-install against a committed lock file:

  * every plugin in `.claude-plugin/marketplace.json` must carry a pinned
    version AND a `plugins.lock.json` entry recording a sha256 tree hash of
    its content;
  * verification recomputes each plugin directory's tree hash and REJECTS
    (exit 1) any unpinned entry, missing/stale lock entry, version drift
    (marketplace vs plugin.json vs lock), or content-hash mismatch;
  * nothing is ever silently accepted — an empty or absent lock file fails
    every plugin, closed.

Usage:
    python3 scripts/verify_plugins.py            # verify (install time + CI)
    python3 scripts/verify_plugins.py --update   # maintainers: relock after a
                                                 # reviewed plugin change

Trust boundary honesty: the lock lives in the same repo as the plugins, so
an attacker who can rewrite repo history can rewrite the lock too. What the
lock buys: (1) a tampered *checkout* (post-clone modification, MITM'd
partial fetch, a stray local edit) diverges from the reviewed lock and is
rejected; (2) plugin changes become a single reviewable artifact — a diff
that touches `plugins/` without touching `plugins.lock.json` fails CI; and
(3) out-of-band verification gets one small file to compare against a known
-good copy. It does NOT protect against a fully compromised upstream repo —
that requires commit signing / out-of-band lock distribution.

Stdlib only; py>=3.10.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

LOCK_VERSION = 1
ALGORITHM = "sha256-tree-v1"

# Interpreter/OS droppings excluded from the tree hash.
_EXCLUDED_DIRS = {"__pycache__", ".git"}
_EXCLUDED_FILES = {".DS_Store"}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _default_paths(root: Path) -> tuple[Path, Path]:
    return root / ".claude-plugin/marketplace.json", root / "plugins.lock.json"


def compute_tree_hash(plugin_dir: Path) -> str:
    """Deterministic sha256 over relative paths + file contents."""
    h = hashlib.sha256()
    files = []
    for p in plugin_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(plugin_dir)
        if any(part in _EXCLUDED_DIRS for part in rel.parts):
            continue
        if rel.name in _EXCLUDED_FILES or rel.suffix in _EXCLUDED_SUFFIXES:
            continue
        files.append(rel)
    for rel in sorted(files, key=lambda r: r.as_posix()):
        h.update(rel.as_posix().encode())
        h.update(b"\0")
        h.update(hashlib.sha256((plugin_dir / rel).read_bytes()).digest())
        h.update(b"\0")
    return h.hexdigest()


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _plugin_json_version(root: Path, source: str) -> str | None:
    pj = _load_json(root / source / ".claude-plugin/plugin.json")
    return pj.get("version") if isinstance(pj, dict) else None


def verify(marketplace_path: Path, lock_path: Path, root: Path) -> list[str]:
    """Return a list of rejection reasons; empty list == verified."""
    errors: list[str] = []
    market = _load_json(Path(marketplace_path))
    if not isinstance(market, dict) or not isinstance(market.get("plugins"), list):
        return [f"unreadable marketplace manifest: {marketplace_path}"]

    lock = _load_json(Path(lock_path))
    locked: dict[str, dict] = {}
    if not isinstance(lock, dict) or not isinstance(lock.get("plugins"), dict):
        errors.append(
            f"missing or unreadable lock file: {lock_path} — refusing all plugins "
            "(fail closed; maintainers: run verify_plugins.py --update)"
        )
    else:
        locked = lock["plugins"]

    seen: set[str] = set()
    for entry in market["plugins"]:
        name = entry.get("name", "<unnamed>")
        seen.add(name)
        version = entry.get("version")
        source = entry.get("source")
        if not version:
            errors.append(f"{name}: no version pin in marketplace.json — rejected")
            continue
        if not source or not source.startswith("./"):
            errors.append(f"{name}: non-local or missing source {source!r} — rejected")
            continue
        pin = locked.get(name)
        if pin is None:
            errors.append(f"{name}: no entry in {Path(lock_path).name} — rejected")
            continue
        if pin.get("version") != version:
            errors.append(
                f"{name}: version drift — marketplace pins {version}, "
                f"lock records {pin.get('version')} — rejected"
            )
            continue
        pj_version = _plugin_json_version(Path(root), source)
        if pj_version != version:
            errors.append(
                f"{name}: version drift — plugin.json says {pj_version}, "
                f"lock records {version} — rejected"
            )
            continue
        plugin_dir = Path(root) / source
        if not plugin_dir.is_dir():
            errors.append(f"{name}: source directory {source} missing — rejected")
            continue
        actual = compute_tree_hash(plugin_dir)
        if actual != pin.get("tree_sha256"):
            errors.append(
                f"{name}: content hash mismatch — plugin tree does not match its "
                f"pin (expected {str(pin.get('tree_sha256'))[:16]}…, got {actual[:16]}…) — rejected"
            )

    for name in sorted(set(locked) - seen):
        errors.append(f"{name}: lock entry has no marketplace counterpart — stale lock, rejected")
    return errors


def update_lock(marketplace_path: Path, lock_path: Path, root: Path) -> None:
    """Regenerate the lock from the current tree (maintainer action)."""
    market = _load_json(Path(marketplace_path))
    if not isinstance(market, dict) or not isinstance(market.get("plugins"), list):
        raise SystemExit(f"unreadable marketplace manifest: {marketplace_path}")
    plugins: dict[str, dict] = {}
    for entry in market["plugins"]:
        name, version, source = entry.get("name"), entry.get("version"), entry.get("source")
        if not (name and version and source):
            raise SystemExit(
                f"refusing to lock unpinned/incomplete marketplace entry: {entry!r} "
                "(every plugin needs name, version, and a local source)"
            )
        plugins[name] = {
            "version": version,
            "source": source,
            "tree_sha256": compute_tree_hash(Path(root) / source),
        }
    Path(lock_path).write_text(
        json.dumps(
            {"version": LOCK_VERSION, "algorithm": ALGORITHM, "plugins": plugins},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--marketplace", type=Path, default=None)
    ap.add_argument("--lock", type=Path, default=None)
    ap.add_argument("--update", action="store_true",
                    help="regenerate the lock from the current tree (maintainers only)")
    args = ap.parse_args(argv)
    marketplace = args.marketplace or _default_paths(args.root)[0]
    lock = args.lock or _default_paths(args.root)[1]

    if args.update:
        update_lock(marketplace, lock, args.root)
        print(f"lock written: {lock}")
        return 0

    errors = verify(marketplace, lock, args.root)
    if errors:
        print("plugin verification FAILED (fail closed — nothing installed/trusted):",
              file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("all marketplace plugins verified against plugins.lock.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
