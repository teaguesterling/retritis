"""The run driver: reset fixture -> run agent -> capture -> check.

HONEST STATUS: `reset_fixture` and `score` are real and runnable today.
`run_agent` is the genuine sub-deliverable the advisor flagged (drive a full
agent through an observe->act->learn cycle). It is stubbed in two modes:
  - "proxy": no agent; score a candidate action (or the fixture as-is) against
    the scenario check. Lets the corpus + check + metrics machinery run E2E now.
  - "full":  drive a real Claude Code / SDK agent on goal.md. TODO.

Run the OFF baseline with the proxy first to validate the rig, then build the
full driver (its own T1) before trusting T3 cost metrics.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from config import CalibrationConfig
from metrics import RunRecord
from toggles import env_for


def load_scenario(corpus_dir: Path, sid: str) -> dict:
    d = corpus_dir / sid
    fixture_ref = (d / "fixture.ref").read_text().strip() if (d / "fixture.ref").exists() else ""
    labels = {}
    if (d / "labels.toml").exists():
        labels = tomllib.loads((d / "labels.toml").read_text())
    return {"id": sid, "dir": d, "goal": (d / "goal.md").read_text(), "fixture_ref": fixture_ref, "labels": labels}


def reset_fixture(scenario: dict, cfg: CalibrationConfig, work: Path) -> Path:
    """Materialize the fixture at its ref in a throwaway git worktree (no edits to the
    live checkout). fixture.ref is 'repo@gitref', repo resolved under fixtures_root."""
    repo, _, ref = scenario["fixture_ref"].partition("@")
    src = cfg.fixtures_root / repo
    if work.exists():
        subprocess.run(["git", "-C", str(src), "worktree", "remove", "--force", str(work)], check=False)
    subprocess.run(["git", "-C", str(src), "worktree", "add", "--detach", str(work), ref or "HEAD"],
                   check=True, capture_output=True)
    return work


def score(scenario: dict, fixture: Path, env: dict[str, str]) -> tuple[bool, str, dict]:
    """Run the scenario's declarative check against the fixture (checks.run_check)."""
    import checks
    return checks.run_check(scenario["dir"], fixture, env)


def run_agent(scenario: dict, fixture: Path, cfg: CalibrationConfig, rec: RunRecord) -> None:
    """OFF/baseline: in proxy mode we do not drive an agent; we measure the fixture
    as-is (a buggy fixture fails its check -> the baseline 'cost' of the unaided state).
    FULL mode (TODO) drives a real agent on goal.md and captures turns/tokens/walltime
    + the kibitzer/blq trace."""
    if cfg.runner_mode == "full":
        raise NotImplementedError("full-agent driver: drive Claude Code/SDK on goal.md, capture trace (TODO)")
    # proxy mode: nothing to do; score() reflects the fixture's current state.


def run_one(sid: str, cfg: CalibrationConfig, run_idx: int) -> RunRecord:
    import checks
    scenario = load_scenario(cfg.corpus_dir, sid)
    rec = RunRecord(scenario=sid, integrations=cfg.label().split(".")[-1], run=run_idx)
    spec = checks.load_check(scenario["dir"])
    if spec.get("type") == "pending":
        rec.detail = f"PENDING -- blocked on {spec.get('blocked_on', '?')}"
        return rec
    work = cfg.out_dir / "_work" / f"{sid}.{cfg.label()}.{run_idx}"
    t0 = time.time()
    fixture = reset_fixture(scenario, cfg, work)
    env = env_for(cfg.integrations, fixture)          # raises if an ON toggle isn't built yet
    run_agent(scenario, fixture, cfg, rec)
    rec.passed, rec.detail, extra = score(scenario, fixture, env)
    if extra.get("latency_ms") is not None:
        rec.tool_latencies_ms.append(extra["latency_ms"])
    rec.walltime_s = round(time.time() - t0, 2)
    return rec


def run_all(cfg: CalibrationConfig) -> Path:
    """Run every scenario x n_runs under the current integration set; write one jsonl.
    Pending checks (workstream not built) are recorded, not skipped, so the corpus
    coverage is visible. Returns the results path."""
    from metrics import write_records
    records = []
    for sid in cfg.scenarios:
        for i in range(cfg.n_runs):
            try:
                records.append(run_one(sid, cfg, i))
            except NotImplementedError as e:
                rec = RunRecord(scenario=sid, integrations=cfg.label().split(".")[-1], run=i)
                rec.detail = f"toggle-not-built: {e}"
                records.append(rec)
    out = cfg.out_dir / f"{cfg.label()}.jsonl"
    write_records(records, out)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--all":
        # OFF/proxy baseline over the whole corpus (the calibration run)
        n = int(args[1]) if len(args) > 1 else 5
        cfg = CalibrationConfig(scenarios=[], n_runs=n)
        cfg.scenarios = sorted(d.name for d in cfg.corpus_dir.iterdir()
                               if d.is_dir() and not d.name.startswith(("_", ".")))
        out = run_all(cfg)
        print(f"wrote {out}  ({len(cfg.scenarios)} scenarios x {n} runs)")
    else:
        # smoke: one OFF/proxy run of each scenario named on argv (defaults to S01)
        ids = args or ["S01_toolinfo_subscript"]
        cfg = CalibrationConfig(scenarios=ids)
        for sid in ids:
            r = run_one(sid, cfg, 0)
            print(json.dumps({"scenario": r.scenario, "passed": r.passed,
                              "walltime_s": r.walltime_s, "detail": r.detail[:160]}))
