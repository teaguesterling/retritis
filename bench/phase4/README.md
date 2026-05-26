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

## Full agent runner (`runner_mode="full"`)
Implemented: `run_agent` drives `claude -p --output-format json --permission-mode acceptEdits
--max-budget-usd <cap>` in the fixture worktree, then `score` checks whether the agent's
edits make the check pass. This is the A-loop machine (integrations OFF = unaided baseline;
ON = with a seeded ratchet, once workstream A exists).

**Validated 2026-05-26:** one unaided S01 run drove the agent end-to-end (44.6s), reset the
fixture, and scored — proving the machine works. Two refinements before trusting A/B cost
numbers: (1) the agent did not resolve S01 under the $0.50 cap (raise the budget for real
A/B runs), and (2) `num_turns`/`usage` JSON keys returned null — verify against the actual
`claude -p` json schema. Cost metrics aren't needed until the A/B runs (post-workstream-A),
so these are deferred, not blocking.

## Status
Corpus (16) + harness + OFF/proxy baseline + calibrated C bars: **done** (see
`../../vision/phase-4-baseline.md`). Full runner: **built + validated functional**. Next:
build workstream C (the cheap unblock), then re-baseline A/B cost with the full runner once
A exists.
