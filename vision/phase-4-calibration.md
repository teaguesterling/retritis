# Phase 4 — calibration pass (concrete checklist)

> The ½–1 day pass that **precedes** workstreams C/B/A ([phase-4.md](./phase-4.md) §1.5).
> Purpose: replace the plan's placeholder T3 bars with bars *calibrated from a real
> baseline*, lock the two day-one decisions, and stand up the measurement rig. Output is a
> committed `vision/phase-4-baseline.md` (numbers) + the harness skeleton + the blq-captured
> baseline run. Nothing here changes suite code — it builds the corpus and measures the
> *current* behavior.

## A. The scenario corpus (build this first)

~18 scenarios, drawn from **real** suite history so the baseline reflects actual work — not
synthetic toys. Several are this session's genuine failures. Each scenario is a directory
`bench/phase4/corpus/<id>/` with: a `fixture/` repo state (or a git ref to check out), a
`goal.md` (the task or the failure to resolve), a `check.py` (automatic pass/fail), and a
`labels.toml` (expected fix / expected verdict — ground truth for adoption & false-promotion
scoring).

| id | archetype | source / fixture | goal | `check.py` asserts | feeds |
|---|---|---|---|---|---|
| S01 | API-drift compat break | fledgling @ pre-`pluckit-0.13` (ToolInfo subscript) | make pro-server tests pass | `pytest test_pro_*` green | A, C |
| S02 | module rename | pluckit `plugins`→`pluckins` import | resolve `ModuleNotFoundError` | import + e2e test green | A |
| S03 | path-join bug | fledgling `read_source` git-path doubling | `ReadLines@HEAD` returns file | reads expected lines | A, C |
| S04 | stale test after API change | `FindInAST`→`FindCode` | fix the "Tool not found" tests | conformance test green | A |
| S05 | dormant feature | squackit FTS unbuilt index | `search_code` returns hits | non-empty ranked result | C(FTS), A |
| S06 | find callers | any suite repo | locate a symbol + its callers | matches known call-graph | C(latency) |
| S07 | investigate symbol | any suite repo | summarize a symbol + recent changes | mentions the real recent commit | C(latency) |
| S08 | out-of-scope edit (denied) | fixture w/ `.umw` scoping `src/auth/**` to review-mode | agent edits `src/auth` in wrong mode | **blocked by kibitzer AND lackpy** | B |
| S09 | in-scope edit (allowed) | same fixture | edit a permitted file | allowed (no false-deny) | B |
| S10 | tool over max-level | `.umw` caps `max-level: 2` | a level-4 tool requested | denied by policy | B |
| S11 | tool under cap (allowed) | same | a level-2 tool requested | allowed | B |
| S12–S15 | **repeat failures** | S01/S03/S05 + 1 new, with a **seeded ratchet** | same failure, 2nd encounter | resolved; surfaced fix matches `labels.toml` | A (headline) |
| S16–S18 | code-nav under hooks | 3 repos | navigate while kibitzer hooks fire | task done within hook time budget | C(coaching), latency |

> The repeat-failure rows (S12–S15) are the A/B's whole point: their baseline is run with an
> **empty** ratchet store (loop-off); the on-run uses a store **seeded** from S01/S03/S05 and
> then **frozen** (phase-4.md §4 T2).

**Checklist**
- [ ] Create `bench/phase4/corpus/` with the 18 scenario dirs.
- [ ] For each: `fixture/` (or `fixture.ref`), `goal.md`, `check.py`, `labels.toml`.
- [ ] `check.py` returns `{passed: bool, detail: str}` and is deterministic (no network, fixed input).
- [ ] Smoke-run every `check.py` against a *known-good* and *known-bad* state to confirm it discriminates.

## B. The baseline harness skeleton (`bench/phase4/`)

This is a **real sub-deliverable**, not a reuse of `prompt_eval` (which scores single model
outputs). It drives a full agent through a cycle on a fixture and scores the outcome. Layout:

```
bench/phase4/
  corpus/<id>/{fixture,goal.md,check.py,labels.toml}
  config.py        # CalibrationConfig
  toggles.py       # how each integration is turned OFF vs ON
  runner.py        # reset fixture → run agent → capture → check  (the hard part)
  metrics.py       # per-run record schema + extractors
  report.py        # results/*.jsonl → markdown (off-vs-on deltas, bar verdicts)
  results/         # <scenario>.<off|on>.<run>.jsonl  +  baseline.md
```

```python
# config.py
@dataclass
class CalibrationConfig:
    scenarios: list[str]                 # corpus ids
    integrations: dict[str, bool]        # {"C": False, "B": False, "A": False}  (off = baseline)
    n_runs: int = 5                      # statistical validity (mean ± stdev)
    model: str = "qwen3:14b-iq4xs"       # local GPU on longbottom; fix seed where possible
    out_dir: Path = Path("results")
```

**`runner.py` (the hard part — spec it honestly).** Per `(scenario, integrations, run)`:
1. **reset** the fixture (`git checkout`/clean a throwaway worktree);
2. **run the agent** on `goal.md` with the integrations toggled (§toggles), capturing the
   tool-call trace **through blq** (so each run is itself a queryable artifact);
3. **score** via `check.py` (success) + `labels.toml` (adoption, false-promotion);
4. **record** a `metrics.py` row.

> Driving a *real* agent through step 2 is the genuine machine. If standing up the full
> agent runner is too heavy for the calibration pass, **fall back to a scoring proxy** the
> existing harness can run — score the agent's *first proposed action* against
> `labels.toml`'s expected fix — and label every proxy metric as such (it under-measures the
> multi-turn win but de-risks the bars). Decide proxy-vs-full in step E.1; either way
> `runner.py` gets its own T1 (it resets cleanly, toggles correctly, scores deterministically).

**`toggles.py` — how off/on is realized (must be clean or the A/B is meaningless):**

| Integration | OFF (baseline) | ON |
|---|---|---|
| **C** substrate | `fledgling.connect(persist=None)` → in-memory rebuild | `connect(persist=.fledgling/cache.duckdb)` |
| **B** policy | kibitzer config.toml only (`PolicyConsumer.from_db`→None) | compiled `.umwelt/policy.db` present |
| **A** loop | empty/absent ratchet store | seeded-then-frozen ratchet store |

## C. Metrics captured at baseline (per workstream)

```python
# metrics.py — one record per (scenario, integration-set, run)
{ "scenario","integrations","run",
  "passed": bool, "turns": int, "tokens": int, "walltime_s": float,
  "tool_latencies_ms": [..],          # C: per query/tool call
  "coaching_fired": int,              # kibitzer events
  "doc_context_coaching_fired": int,  # the affordable-only-with-C kind
  "staleness_violation": bool,        # C: served pre-edit facts?
  "policy_verdict": {"kibitzer":..,"lackpy":..,"truth":..},  # B
  "surfaced_fix": str|None, "took_surfaced_fix": bool,       # A: adoption
  "surfaced_fix_correct": bool|None } # A: vs labels.toml → false-promotion
```

- **C:** `tool_latencies_ms` → p50/p95; `doc_context_coaching_fired` rate; `staleness_violation` count.
- **B:** verdict triples → divergence count (kibitzer vs lackpy vs truth); false-deny on S09/S11.
- **A:** `turns`/`tokens`/`walltime_s` on repeat scenarios (S12–S15); adoption rate; false-promotion rate.

Run the **whole corpus, all integrations OFF, N=5**, into `results/`. That's the baseline.

## D. Pin the bars (from the baseline, then commit them)

Replace phase-4.md's placeholders with baseline-derived bars and record both. Suggested forms:

| Metric | Bar (calibrate from baseline B) | Rationale |
|---|---|---|
| C: repeated-query p95 | `< max(50ms, 0.1 · B_p95)` | order-of-magnitude faster than rebuild |
| C: doc-context coaching fire | `≥ 95%` of hooks within budget (baseline ≈ 0%) | the capability becomes affordable |
| C: staleness violations | `= 0` (absolute) | correctness, not perf |
| B: kibitzer/lackpy divergence | `= 0` over the generated conformance corpus | safety invariant |
| B: false-deny (S09/S11) | `≤ 2%` (or baseline-of-config if higher) | don't over-block |
| A: repeat-failure turns/tokens | `≤ 0.7 · B_repeat_median`, mean over N, stdev shown | ≥30% cheaper on repeats |
| A: false-promotion | `≤ 10%`, and **a bar inside one stdev of baseline is NOT cleared** | precision floor / anti-noise |

**Honesty rule (binding):** the bar is whatever this step records *before* any on-run. No
post-hoc adjustment. A workstream that later misses its bar is "don't ship yet," recorded as
such — not "retune the metric."

**Checklist**
- [ ] Baseline run complete (corpus × OFF × N=5) in `results/`.
- [ ] `report.py` renders baseline distributions (median, p95, stdev) per metric.
- [ ] Bars computed from the formulas above, written into `vision/phase-4-baseline.md` with
      their baseline values beside them, and the matching lines in phase-4.md §§2–4 updated to
      cite the calibrated number.

## E. Lock the day-one decisions (calibration must settle these)

- [ ] **E.1 Runner: full-agent vs scoring-proxy.** Pick based on effort budget; record the
      choice + its measurement caveats. (Full agent measures the real multi-turn win; proxy
      de-risks but under-measures.)
- [ ] **E.2 A — promote mode.** v1 = **explicit `ratchet-promote`** (phase-4.md §4/§8.2):
      lower false-promotion risk, deterministic T2. Confirm and record.
- [ ] **E.3 C — concurrency model.** v1 = **builder-on-demand + file lock + last-good
      snapshot** (phase-4.md §2). Confirm and record.
- [ ] **E.4 Ratchet consumer home.** Decide kibitzer (coaching) / lackpy (seeding) / both
      (phase-4.md §8.1) — determines where A's `RatchetConsumer` lives.
- [ ] **E.5 Cache dir layout.** `.bird` + `.fledgling/cache.duckdb` + `.umwelt/policy.db`
      under one `.retritis/`? (gitignore + ergonomics; phase-4.md §8.3)

## F. Definition of done for the calibration pass

- [ ] 18-scenario corpus built, each `check.py` discriminates good/bad.
- [ ] `bench/phase4/` harness skeleton runs the OFF baseline end-to-end (full or proxy), N=5.
- [ ] `vision/phase-4-baseline.md` committed: baseline distributions + the pinned bars.
- [ ] E.1–E.5 decisions recorded.
- [ ] Everything committed (signed) + the baseline run captured in blq.

Only then do C and B start — against real bars, a working rig, and settled decisions.
```
