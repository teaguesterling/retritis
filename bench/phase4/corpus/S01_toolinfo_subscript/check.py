#!/usr/bin/env python3
"""S01 success check: does fledgling's pro server build cleanly?

Runs the one pro test that constructs a fresh server (the code path the
ToolInfo-subscript bug errors on). Imports fledgling FROM THE FIXTURE via
PYTHONPATH so we test the fixture's code, not whatever is editable-installed
in the venv. Deps (pluckit, fastmcp, duckdb) still come from the venv.

Usage: python check.py <fixture_dir>
Prints one JSON line: {"passed": bool, "detail": str}
"""
import json
import os
import subprocess
import sys
from pathlib import Path

TEST = "tests/test_pro_resources.py::TestResourcesWorkWithoutToolCalls::test_fresh_server_resources"


def main() -> None:
    fixture = Path(sys.argv[1]).resolve()
    env = dict(os.environ)
    # Fixture's package must win over any editable install. For setuptools' default
    # (lenient) editable, PYTHONPATH is searched before the site-packages .pth dir,
    # so this shadows it. If a strict/meta-path editable is in use it may NOT —
    # see runner.py / README: real isolation may require a per-fixture venv.
    env["PYTHONPATH"] = str(fixture) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONNOUSERSITE"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", TEST, "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=str(fixture), env=env, capture_output=True, text=True, timeout=240,
        )
        tail = (proc.stdout.strip().splitlines() or [""])[-1]
        print(json.dumps({"passed": proc.returncode == 0,
                          "detail": tail or proc.stderr.strip()[-200:]}))
    except subprocess.TimeoutExpired:
        print(json.dumps({"passed": False, "detail": "timeout"}))


if __name__ == "__main__":
    main()
