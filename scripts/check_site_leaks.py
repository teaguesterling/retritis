"""check_site_leaks — refuse to deploy internal material to the public site.

The site builds from docs/, which also holds internal working files
(briefs with SSH hops and session links, superpowers specs/plans, RFCs).
Sphinx publishes any source that is not excluded, so this scans the BUILT
output, not the config: a drifted exclude_patterns cannot get past it.

    python3 scripts/check_site_leaks.py docs/_build/html

Exit 0: no leaks (prints "ok: <n> files scanned").
Exit 1: leaks found (prints one "<relpath>: <reason>" per leak).
Exit 2: no index.html in the build dir — an empty build is not a pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

PATH_MARKERS = ("briefs/", "superpowers/", "rfcs/")
CONTENT_MARKERS = ("ssh ionos", "claude.ai/code/session_")
SCANNED_SUFFIXES = (".html", ".txt")


def find_leaks(root: Path) -> list[str]:
    leaks = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        hit = next((m for m in PATH_MARKERS if m in rel + "/"), None)
        if hit:
            leaks.append(f"{rel}: internal folder {hit}")
            continue
        if p.suffix in SCANNED_SUFFIXES:
            text = p.read_text(errors="replace")
            hit = next((m for m in CONTENT_MARKERS if m in text), None)
            if hit:
                leaks.append(f"{rel}: contains {hit!r}")
    return leaks


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(argv[1])
    if not (root / "index.html").is_file():
        print(f"no index.html in {root}: refusing to pass an empty build",
              file=sys.stderr)
        return 2
    leaks = find_leaks(root)
    for leak in leaks:
        print(leak)
    if leaks:
        return 1
    n = sum(1 for p in root.rglob("*") if p.is_file())
    print(f"ok: {n} files scanned")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
