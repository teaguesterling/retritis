"""Declarative scenario checks. A scenario carries a `check.toml`:

    type = "pytest"              # run a pytest target against the fixture, isolated
    target = "tests/..::..::.."
    expect = "pass"              # "pass" (exit 0) | "fail" (non-zero) — default "pass"

    type = "command"             # run a shell command in the fixture
    cmd = "squackit search 'foo' --json"
    contains = "def foo"         # optional substring assertion on stdout
    expect = "pass"

    type = "pending"             # the check needs a workstream that isn't built yet
    blocked_on = "B"             # records why it can't run; never "passes" silently

Returns (passed: bool, detail: str, extra: dict) where extra may carry latency_ms.

Fixture isolation: pytest/command run with PYTHONPATH=<fixture> so the fixture's
package wins over the editable install (validated for setuptools lenient editable in
S01; a strict/meta-path editable would need a per-fixture venv — see runner.venv_isolate).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path


def load_check(scenario_dir: Path) -> dict:
    p = scenario_dir / "check.toml"
    return tomllib.loads(p.read_text()) if p.exists() else {"type": "missing"}


def _isolated_env(fixture: Path, extra_env: dict[str, str]) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(fixture) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONNOUSERSITE"] = "1"
    env.update(extra_env)
    return env


def run_check(scenario_dir: Path, fixture: Path, extra_env: dict[str, str] | None = None) -> tuple[bool, str, dict]:
    spec = load_check(scenario_dir)
    env = _isolated_env(fixture, extra_env or {})
    t = spec.get("type")
    expect_pass = spec.get("expect", "pass") == "pass"

    if t == "pytest":
        cmd = [sys.executable, "-m", "pytest", spec["target"], "-q", "--no-header", "-p", "no:cacheprovider"]
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=str(fixture), env=env, capture_output=True, text=True, timeout=300)
        ms = (time.time() - t0) * 1000
        ok = (proc.returncode == 0) == expect_pass
        tail = (proc.stdout.strip().splitlines() or [""])[-1]
        return ok, tail or proc.stderr.strip()[-200:], {"latency_ms": round(ms, 1)}

    if t == "command":
        t0 = time.time()
        proc = subprocess.run(spec["cmd"], cwd=str(fixture), env=env, capture_output=True,
                              text=True, timeout=300, shell=True)
        ms = (time.time() - t0) * 1000
        ok = (proc.returncode == 0) == expect_pass
        if ok and "contains" in spec:
            ok = spec["contains"] in proc.stdout
        return ok, (proc.stdout or proc.stderr)[-200:], {"latency_ms": round(ms, 1)}

    if t == "script":
        script = Path(__file__).parent / spec["script"]
        cmd = [sys.executable, str(script), *[str(a) for a in spec.get("args", [])]]
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=str(fixture), env=env, capture_output=True, text=True, timeout=300)
        ms = (time.time() - t0) * 1000
        ok = (proc.returncode == 0) == expect_pass
        return ok, (proc.stdout or proc.stderr).strip()[-200:], {"latency_ms": round(ms, 1)}

    if t == "pending":
        return False, f"PENDING — blocked on workstream {spec.get('blocked_on','?')}", {"pending": True}

    return False, f"unknown check type: {t}", {}
