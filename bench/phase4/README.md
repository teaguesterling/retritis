# bench/phase4 — Phase 4 calibration + benchmark harness

Skeleton for the rig described in [`../../vision/phase-4-calibration.md`](../../vision/phase-4-calibration.md).
Builds the scenario corpus, runs it with integrations toggled OFF (baseline) or ON,
and reports off-vs-on deltas to gate each workstream's T3 usefulness bar.

## Layout
- `config.py` — `CalibrationConfig` (scenarios, integration toggles, n_runs, runner mode).
- `metrics.py` — `RunRecord` schema + jsonl IO + mean/stdev aggregation.
- `toggles.py` — how each integration is realized OFF vs ON. **ON paths raise
  `NotImplementedError`** until Phase 4 builds them (so a premature ON run fails loudly).
- `runner.py` — reset fixture (git worktree) → run agent → score via the scenario's
  `check.py`. **`reset_fixture` + `score` are real; `run_agent` is the genuine
  sub-deliverable** (drive a full agent) and is stubbed: `proxy` mode measures the
  fixture as-is; `full` mode is TODO.
- `report.py` — `results/*.jsonl` → markdown (mean ± stdev, deltas, bar verdicts).
- `corpus/<id>/` — `goal.md`, `check.py`, `labels.toml`, `fixture.ref`. **S01 is complete.**

## Run the OFF/proxy smoke (validates corpus + check + metrics machinery)
```bash
cd bench/phase4
python runner.py S01_toolinfo_subscript     # buggy fixture → check fails (correct baseline)
python corpus/S01_toolinfo_subscript/check.py ~/Projects/fledgling         # the FIXED working tree → check passes
```

## Known constraint surfaced by S01 (read before building `runner.py`)
**Fixture isolation vs editable installs.** The suite tools are `pip install -e`'d, so
"import fledgling" may resolve to the editable source rather than the fixture, silently
making a *buggy* fixture pass and invalidating the baseline. `check.py` uses
`PYTHONPATH=<fixture>` (which wins for setuptools' default lenient editable). If a
strict/meta-path editable is ever used, the only robust fix is a **per-fixture venv**.
`runner.py`'s `reset_fixture` should grow that isolation before the baseline is trusted —
this is a real T1 requirement for the runner, not a footnote.

## Status
Scaffold + S01. Next per the calibration doc: flesh the remaining ~17 scenarios, build the
`full` runner (its own T1), run the OFF baseline N=5, pin bars into `vision/phase-4-baseline.md`.
