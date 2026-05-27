# Phase 4 — baseline & pinned bars

> Output of the calibration pass ([phase-4-calibration.md](./phase-4-calibration.md)).
> Replaces the placeholder T3 bars in [phase-4.md](./phase-4.md) §§2–4 with numbers
> derived from a real baseline run. **Binding honesty rule:** these bars were set from
> the baseline *below*, before any ON run; they are not adjusted post-hoc.

## Run metadata

- Date: 2026-05-26 · host: longbottom · corpus: 16 scenarios × N=5 (`bench/phase4/`)
- Mode: **OFF / proxy** (`runner_mode=proxy`, all integrations off). Proxy measures the
  fixture as-is + check; it does **not** drive a full agent, so turns/tokens are unmeasured
  here (that needs the `full` runner — see Limits).
- Artifact: `bench/phase4/results/proxy.baseline.jsonl` (80 records).

## Baseline per scenario

| scenario | feeds | pass (OFF) | latency mean / p95 | note |
|---|---|---|---|---|
| S01 toolinfo_subscript | A,C | 0/5 | 4091 / 4259 ms | unaided buggy fails (correct) |
| S02 pluckit_module_rename | A | 0/5 | 678 / 690 ms | unaided fails |
| S03 read_source_path_doubling | A,C | 0/5 | 1581 / 1606 ms | unaided fails |
| S04 findinast_removed | A | 0/5 | 621 / 666 ms | unaided fails |
| S05 squackit_fts_dormant | C,A | — | — | PENDING (squackit fixture+venv) |
| **S06 fts_search_cold** | **C** | 5/5 | **4221 / 4349 ms** | cold connect+rebuild_fts+search |
| **S07 fts_build_cost** | **C** | 5/5 | **4194 / 4242 ms** | cold connect+rebuild_fts (6470 FTS rows) |
| S08–S11 policy_conformance | B | — | — | PENDING (workstream B) |
| S12–S15 repeat_failure | A | — | — | PENDING (workstream A) |
| S16 codenav_under_hooks | C | — | — | PENDING (workstream C) |

The A-failure scenarios (S01–S04) fail 0/5 unaided — that's the point: the **learn loop**
must make *repeats* of these resolve faster (measured by the full runner). The C scenarios
(S06/S07) give the cold-substrate cost the persistent cache must beat.

## Pinned bars (calibrated)

| Metric | Baseline | **Bar** | Status |
|---|---|---|---|
| **C** · repeated FTS/AST query p95 | 4349 ms (cold) | **< 435 ms** (≤ 0.1× baseline) | measurable now via S06/S07 ON |
| **C** · FTS build cost p95 | 4242 ms | **< 425 ms** when cache-attached | measurable now |
| **C** · doc-context coaching fire rate | ~0% (too slow) | **≥ 95%** within hook budget | needs C built (S16) |
| **C** · staleness violations | 0 | **= 0** (absolute) | invariant |
| **A** · repeat-failure turns/tokens | unaided 0/5 pass | **≤ 0.7× full-runner baseline** | PROVISIONAL — needs `full` runner + workstream A |
| **A** · false-promotion rate | n/a | **≤ 10%**, & must beat baseline by > 1σ | PROVISIONAL — needs workstream A |
| **B** · kibitzer↔lackpy divergence | n/a | **= 0** over generated conformance corpus | PROVISIONAL — needs workstream B |
| **B** · false-deny (S09/S11) | n/a | **≤ 2%** | PROVISIONAL — needs workstream B |

The **C** bars are real (calibrated from S06/S07). The **A/B** bars stay PROVISIONAL until
their workstream exists *and* the `full` runner can baseline cost on real agent runs — the
proxy can't measure turns/tokens. Re-baseline A/B cost when the full runner lands; record
the revised number here with its reason.

## Locked decisions (calibration §E)

- **E.1 Runner:** proxy now (validates the rig + C bars); `full` agent driver is the next
  build (its own T1) before any A/B cost bar is trusted.
- **E.2 A promote-mode:** **explicit `ratchet-promote`** (deterministic T2, lower
  false-promotion). Revisit auto-promote after the precision bar clears.
- **E.3 C concurrency:** **builder-on-demand + file lock + last-good snapshot** (no daemon
  in v1).
- **E.4 Ratchet consumer home:** **kibitzer** (in-session coaching) as primary; lackpy
  seeding is a follow-on. (Reuses kibitzer's `PolicyConsumer` pattern as `RatchetConsumer`.)
- **E.5 Cache dir:** consolidate under **`.retritis/`** (`.retritis/fledgling.duckdb`,
  `.retritis/policy.db`, riggs store), with blq's `.bird` alongside; gitignore the lot.

## Limits of this baseline (honest)

- **Proxy ≠ agent.** No turns/tokens/adoption captured — those are A's headline metrics and
  need the `full` runner. Treat A/B numbers here as scaffolding, not evidence.
- **6 of 16 scenarios run** (S01–S04, S06–S07); 10 are PENDING on their workstream. The
  corpus is complete; runnability grows as C/B/A land.
- **Fixture isolation** validated only for fledgling pytest scenarios (PYTHONPATH shadows
  the lenient editable). squackit-CLI scenarios (S05) need a per-fixture venv — open.

---

## Workstream C — RESULTS (2026-05-26, persist landed)

fledgling `feat/persist-cache` (0.11.0): `connect(persist=, read_only=)` +
`build_cache()`. Measured via `bench/phase4` toggle **C ON** (`results/proxy.C.jsonl`,
5 runs each; run 0 is the cold build-on-demand, runs 1–4 are warm cache hits):

| metric | baseline p95 | bar | C ON p95 | verdict |
|---|---|---|---|---|
| **C** · repeated FTS query (S06) | 4349 ms | < 435 ms | **274 ms** | ✅ MET (16×) |
| **C** · FTS build/attach cost (S07) | 4242 ms | < 425 ms | **232 ms** | ✅ MET (18×) |

The cold build in run 0 (~5.1 s, ≥ the 4349 ms baseline) confirms the new tool builds
no faster — the win is purely the cache hit, so the speedup is conservative. Zero
staleness is enforced by a git-content key (excludes the cache file itself);
`fledgling/tests/test_persist.py` covers round-trip, idempotence, stale-on-change, and
read-only write-rejection (7/7). A follow-up made `Tools` discovery lazy (the ~80 ms
`mcp_list_tools`+catalog scan a read-only reader never needs), cutting read-only
`connect()` ~130→~50 ms — hence 16×/18× rather than 12×/14×.

**Still open for C's full definition-of-done:** `S16 codenav_under_hooks` — doc-context
coaching firing within the kibitzer PreToolUse budget (bar ≥95%). Now *unblocked* by the
cheap cache hit, but the kibitzer-hook wiring + S16 check are a separate next increment.
Concurrency is single-writer (DuckDB-enforced); last-good-snapshot fallback + incremental
per-file rebuild deferred.
