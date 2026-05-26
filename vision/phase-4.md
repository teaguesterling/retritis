# Phase 4 — deep cross-tool integration (detailed plan)

> **Scope.** Close the three loops the suite was built for but never wired end-to-end:
> the **learn loop** (agent-riggs → in-session suggestion), **one-policy-two-enforcers**
> (umwelt → kibitzer + lackpy), and a **persistent fact substrate** (file-backed
> fledgling). Grounded in the actual code (May 2026); each workstream is *wire the last
> connector + verify + measure*, not greenfield. Companion to
> [vision/integrations/](./integrations/) (the further horizon: the same loops spoken
> over goo). Every code change here is a signed commit across agent-riggs / kibitzer /
> lackpy / fledgling (+ maybe umwelt), mostly on snape.

## 0. Corrected current state (verified, not assumed)

The ecosystem guide marks these "open." They are **half-built**; the gaps are narrow:

| Workstream | What already exists | The actual gap |
|---|---|---|
| **A · learn loop** | agent-riggs: full `ingest` → trust EWMA (`_store_turn`/`_store_failure`) → `ratchet/candidates.py` → `ratchet-{promote,reject,history}` CLI, in a **DuckDB store**. It *produces* scored, promoted "ratchets." | **No in-session consumer.** kibitzer doesn't read `ratchet_decisions` back. (The lackpy `trace-log` worktree only *feeds* riggs — producer-side, writes `.lackpy/traces.jsonl` for ingest — not a consumer.) The producer exists; a net-new `RatchetConsumer` is needed. |
| **B · policy** | kibitzer `PolicyConsumer` with 3 levels (`from_db(policy.db)` / `from_engine()` / config-only); lackpy `policy/sources/umwelt.py`; umwelt `compilers/`. | **End-to-end path unverified** + no guarantee kibitzer and lackpy resolve the *same* policy identically. |
| **C · substrate** | fledgling `connect()` (connection.py:354); `rebuild_fts()` → `create_fts_index(overwrite=1)`. | FTS/AST/git facts are **rebuilt in-memory (~2s) per process** — too costly for per-hook coaching. |

So Phase 4 is mostly **connectors, conformance, and measurement** — which is exactly why this plan weights *validation* as heavily as implementation.

## 1. Three tiers of validation (applied to every workstream)

A workstream is **not done when its tests pass**. It's done when it *demonstrably helps the
process*. Every workstream below carries all three:

- **T1 · Unit / integration** — the code is correct in isolation (pytest, in each repo).
- **T2 · E2E scenario** — the cross-tool path runs end-to-end, scripted and repeatable
  (captured through **blq**, so the run is itself a queryable artifact — dogfooding).
- **T3 · Process-usefulness** — an **off-vs-on A/B** over a real scenario corpus, with a
  numeric bar that must clear before the workstream ships. Green T1/T2 is *necessary, not
  sufficient.* The harness for T3 is shared (§5).

> **All T3 bars in this plan are PROVISIONAL.** A number set without a baseline is a
> guess, and the honesty rule (§5) forbids moving it post-hoc — so the bars must be
> *calibrated from a baseline*, not asserted. See the calibration pass below.

### 1.5 Calibration pass — precedes C and B (½–1 day)

Before any workstream executes, run a **baseline + decisions** pass so the bars are real
and the day-one ambiguities are settled:

1. **Build the scenario corpus** (§5) and run it **loop-off / policy-off / in-memory** to
   get baseline distributions for every T3 metric (latency, turns/tokens to resolve,
   coaching-fire rate, etc.).
2. **Pin each T3 bar** from its baseline (e.g. "repeat-failure turns: baseline median M →
   bar = 0.7·M", "p95 latency: baseline P → bar < max(50ms, 0.1·P)"). Record the bar **and
   its baseline** in the workstream before building. The numbers in §§2–4 are *placeholders
   to be replaced here.*
3. **Settle the day-one decisions** that T2 depends on: A's auto-promote-vs-human (§4, §8.2)
   and C's concurrency model (§2). T2 scripts can't be written until these are chosen.

The calibration pass is itself a committed artifact (`vision/phase-4-baseline.md` + the
harness run through blq) — cheap insurance against discovering arbitrary bars mid-build.

> **DONE (2026-05-26):** the calibration rig is built and run. `bench/phase4/` holds the
> 16-scenario corpus + harness (`checks.py`/`runner.py`/`report.py`); the OFF/proxy
> baseline ran (N=5); pinned bars + locked decisions are in
> [phase-4-baseline.md](./phase-4-baseline.md). The **C** latency bar is calibrated from
> real numbers (cold ~4.2s → bar p95 < 435ms); **A/B** cost bars stay provisional until
> the full agent runner baselines them. Workstreams C/B/A can now start against real bars.

---

## 2. Workstream C — persistent fact substrate *(second, after B; a `connect()` signature change + staleness — unblocks A's repeated reads)*

**Target.** A file-backed per-project DuckDB (`.fledgling/cache.duckdb`, co-located with
blq's `.bird`) holding AST + git + FTS. Hooks/tools **attach** instead of rebuilding;
the cache invalidates on file mtime / `HEAD` change and rebuilds only the stale slice.

**Wiring.** *(Code-grounded 2026-05-26: `connect()` today is
`connect(init, root, profile, modules)` — **no `database`/persist knob; the DuckDB is
in-memory**. So C is a signature + plumbing change, not a config toggle — larger than the
"cheap unblock" framing implied.)*
1. Add a persist param — `fledgling.connect(persist=<path>, read_only=<bool>)` — threaded to
   the internal `duckdb.connect(database=…)`; if FTS/AST tables are absent or stale, build;
   else attach. Single-writer (DuckDB): a builder process writes, hook/tool readers open
   `read_only=True`.
2. A **staleness key** per source file: `(path, mtime, blob_sha)`. Rebuild a file's AST/FTS
   rows only when its key changes; `rebuild_fts()` becomes incremental over changed ids.
3. squackit + the kibitzer hook open the shared cache read-only.

**Concurrency model (decide in calibration — DuckDB is single-writer, readers do *not*
snapshot cleanly off a file being written).** Pick one explicitly; this is the engineering
subproject, not a footnote:
- **(a) builder-on-demand + file lock + last-good snapshot** *(recommended v1)* — a reader
  that finds the cache locked/being-built falls back to a frozen last-good copy (or
  in-memory rebuild) rather than reading a torn file. Simplest; no daemon.
- **(b) long-lived builder daemon** serving readers via IPC — cleanest concurrency, but
  now you own a daemon (and it starts to look like the goo `good` daemon — note the
  convergence, don't build it twice).
- **(c) WAL / parquet sidecars** — readers attach immutable parquet snapshots the builder
  swaps atomically. More moving parts.

**Other risks.** (a) **Staleness correctness** — serving facts from before an edit is worse
than slow; the mtime+sha key and explicit "rebuild on miss" are load-bearing. (b) Cache
poisoning across branches — key on `HEAD` too.

**T1.** Unit: staleness key changes on edit; incremental rebuild touches only changed ids;
read-only reader never blocks on a writer; corrupt/locked DB falls back to in-memory.
**T2.** E2E: open project → first `search_code` builds (~2s) → second is cache hit; edit a
file → next query reflects it and *only* that file rebuilt; concurrent reader during a
build returns either old-consistent or new, never torn.
**T3 (usefulness).** Metric set, measured off (in-memory) vs on (persistent):
- p50/p95 latency of a repeated `search_code`/`find` — **bar: p95 < 50 ms on** (from ~2 s).
- kibitzer per-hook **doc-context coaching fire rate** — with cheap FTS it becomes
  affordable inside the PreToolUse budget; **bar: coaching that needs doc-context fires
  within the hook time limit in ≥95% of hooks** (off: ~0%, it was too slow to attempt).
- **Staleness bugs = 0** over the scenario corpus (never serve pre-edit facts).
- Definition of done: p95 bar met **and** doc-context coaching demonstrably fires **and**
  zero staleness — not merely "tests green."

---

## 3. Workstream B — one policy, two enforcers *(do FIRST — smallest + safety-critical; mostly wiring + conformance)*

**Target.** A single `.umw` compiles to `policy.db`; **kibitzer** enforces it in-agent via
`PolicyConsumer.from_db(policy.db)` **and lackpy** validates generated programs against the
**same** `policy.db` via `policy/sources/umwelt.py`. Same authored policy, two surfaces, no
divergence.

**Wiring.**
1. Confirm `umwelt compile --target <policydb>` produces the `policy.db` shape
   `PolicyConsumer.from_db()` + lackpy's source both expect (one schema, two readers).
2. Point both at the same compiled artifact path (project `.umwelt/policy.db`); document
   the compile step (a `make policy` / a pre-commit / a fledgling-cache sibling).
3. **No reimplemented evaluator** — both must resolve through umwelt's `PolicyEngine`
   (kibitzer already does via `from_db`; verify lackpy's source does too, doesn't shadow it).

**Risks.** **Divergence is a security bug, not a nuisance** — if kibitzer and lackpy
disagree on a verdict, the agent believes it's sandboxed differently than enforcement
allows. The conformance test (T2) is the primary safety artifact. Secondary: over-blocking
(false-deny) that makes the policy annoying enough to be disabled.

**T1.** Unit: `PolicyConsumer.from_db` loads a known `policy.db` and returns expected
`ModePolicy` (writable/strategy/coaching_frequency/max_turns); lackpy's umwelt source
returns the matching verdict object; graceful fallback when no policy.db.
**T2 (the safety artifact — a committed test, not an inspection).** A real file
`tests/conformance/policy_agreement.py` that runs in CI, so "0 divergence" is *enforced*,
not asserted once. **Corpus generation (this is what makes "zero divergence" meaningful —
don't hand-pick easy cases):** enumerate `(tool, path)` pairs as the **cross-product of
every selector in the `.umw`** (each rule's path prefix/glob + its boundary cases:
just-inside, just-outside, parent, sibling) **× the tool set**, plus a fuzzed tail
(random paths) to catch default-rule disagreements. For each pair, resolve the *expected*
verdict from umwelt's `PolicyEngine` directly (the ground truth), then assert **kibitzer
(`from_db`) and lackpy (`policy/sources/umwelt`) both match it**. Zero divergence across
the generated corpus is the gate. Plus a live scenario: a lackpy-generated program editing
`src/auth/**` is blocked by the policy *and* kibitzer blocks the same edit in-agent.
**T3 (usefulness).** Off (config.toml only) vs on (compiled `.umw`):
- **divergence count = 0** across the conformance corpus (the headline bar).
- **correct out-of-scope denials** on a held-out set (true positives) with **false-deny
  rate ≤ 2%** (doesn't over-block legitimate edits).
- author effort: one `.umw` replaces N scattered config knobs — record the line-count /
  source-of-truth reduction as a qualitative win.
- Definition of done: 0 divergence, false-deny under bar, one policy file governs both.

---

## 4. Workstream A — close the learn loop *(last; depends on a stable substrate + a clean trace)*

**Target.** A failure pattern observed once becomes an in-session suggestion next time: a
**repeat** failure resolves faster because kibitzer surfaces the promoted fix and/or lackpy
seeds from it. agent-riggs already *promotes*; we wire the **consumer**.

**Wiring.**
1. **The in-session consumer is net-new.** *(Correction from reading the code: the lackpy
   `trace-log` worktree is producer-side — it appends `.lackpy/traces.jsonl` for riggs to
   ingest, **not** a promotion consumer. There is nothing to reconcile with.)* Build a
   `RatchetConsumer` (modeled on kibitzer's `PolicyConsumer`) that reads **promoted rows from
   agent-riggs' `ratchet_decisions` table** (a candidate is `{candidate_key, evidence}`) and
   matches `candidate_key` to the current failure fingerprint. Decide: kibitzer (coaching),
   lackpy (seeding), or both.
2. Define the **read contract**: kibitzer queries agent-riggs' DuckDB ratchet store for
   *promoted* ratchets matching the current context (failure fingerprint / file / tool),
   ordered by trust. Reuse kibitzer's `PolicyConsumer`-style pattern (graceful fallback,
   cached, read-only) — a `RatchetConsumer.from_db(riggs.duckdb)`.
3. kibitzer's PreToolUse/PostToolUse hook surfaces the top promoted match as a coaching
   suggestion; PostToolUse feeds the outcome back to riggs `ingest` (the EWMA already
   updates trust) — closing observe→learn→observe.

**Risks.** (a) **Promotion precision** — a wrong/noisy suggestion is worse than none;
gate on trust threshold + the existing `ratchet-reject` to demote. (b) **The store schema
is the contract** between riggs (producer) and kibitzer (consumer); version it. (c)
Feedback-loop instability — a promoted-then-wrong pattern must decay (EWMA already does;
verify the demotion path fires).

**T1.** Unit: `RatchetConsumer.from_db` returns promoted ratchets above the trust
threshold, ordered; ignores rejected/low-trust; PostToolUse outcome updates the EWMA; bad
outcome demotes below threshold.
**Decide before A starts (calibration §1.5):** **auto-promote at trust-threshold vs
explicit `ratchet-promote`.** v1 recommendation: **explicit promote** (human-in-the-loop)
— lower false-promotion risk, and the T2 script can call `ratchet-promote` deterministically
rather than depending on a threshold-crossing. T2 below assumes this; switch to auto-promote
only after the precision bar (T3) is met on the explicit path.

**T2 (the loop, end-to-end).** The off/on session boundary must be *operationalized* so
"first encounter unaffected" is real: **seed** the ratchet store from a baseline run, then
**freeze** it (read-only) for the measured session — the test session must not promote from
its own run. Script (captured via blq): introduce failure X → riggs ingests + `ratchet-promote`
→ **freeze store** → **fresh session** with the frozen store, same failure X → kibitzer
surfaces the recorded fix → apply → (post-session) a *separate* ingest confirms trust for X
increments. The full observe→understand→act→learn cycle, with a clean session boundary.
**T3 (usefulness — the headline A/B).** Loop **off** vs **on**, over the repeat-failure
corpus (§5):
- **turns / tokens / wall-time to resolve a *repeat* failure** — **bar: ≥30% reduction
  on repeats** (first-encounter unaffected; the win is on the second+ encounter).
- **promoted-fix adoption rate** — how often the surfaced suggestion is the one taken.
- **false-promotion rate** — surfaced suggestions that were wrong/unhelpful — **bar: ≤10%**
  (precision floor; this is the anti-noise gate).
- Definition of done: repeat-failure cost down past the bar **and** false-promotion under
  the floor. Speed without precision fails the workstream.

---

## 5. The usefulness harness (shared T3 infrastructure)

The distinctive bar — *does it help the process* — needs a real measurement rig, not vibes.

- **Scenario corpus.** ~15–25 recurring agent-dev situations drawn from **real** suite
  history: build/test failures captured by blq (the fledgling pluckit-0.13 bugs we just
  fixed are genuine examples), policy-relevant edits (in/out of `src/auth/**`-style
  scopes), and code-navigation tasks. Each scenario: a fixture repo state + a goal + an
  automatic success check.
- **Off-vs-on driver — this is its own deliverable, not a reuse.** lackpy's
  `scripts/prompt_eval/` scores *single model outputs against intents*; T2/T3 here must
  drive a **full agent through an observe→act→learn cycle on a fixture repo with an
  automatic success check** — a different machine. Spec it as a sub-deliverable
  (`phase4/harness`) with its own T1 (the runner is itself tested: it toggles integrations,
  resets fixtures, scores success deterministically). If that's too heavy up front, fall
  back to a **scoring proxy the existing harness *can* run** (e.g. score the agent's first
  proposed action against the known fix) and note the proxy's limits. Don't pretend the
  full driver is free.
- **Statistical validity.** LLM variance will swing a "30% reduction" claim on a single
  run. **Run each scenario N=5 times**, report **mean ± stdev**, and judge bars against the
  mean with the stdev shown (a bar inside one stdev of baseline is not cleared). N×corpus×
  off/on is the compute budget — ~15 scenarios × 5 × 2 = 150 agent runs per workstream;
  size the corpus to that, or raise N and shrink the corpus. Local GPU (`qwen3:14b-iq4xs`
  on longbottom) keeps this affordable; fix seeds where the stack allows.
- **Metrics (per workstream, §§2–4)** logged per run; report renders off-vs-on deltas +
  whether each bar cleared. The harness *itself* runs through blq, so every benchmark run
  is a queryable artifact (dogfooding the observe layer).
- **Honesty rule.** Report the bar that was set *before* the run, and whether it cleared —
  no moving the goalposts after seeing results. Negative results (a workstream that
  doesn't clear its bar) are a valid, recorded outcome: it means "don't ship this yet,"
  not "tune the metric."

## 6. Sequencing, dependencies, logistics

```
   B (policy conformance)  ──▶  C (persistent substrate)  ──▶  A (learn loop)
   smallest · safety-crit.      signature change to            net-new RatchetConsumer
   (PolicyConsumer exists)      fledgling.connect()            + full-agent A/B
```

- **Re-sequenced from the code-grounded assessment (2026-05-26).** The plan first put C as
  the "cheap unblock," but reading the code flipped the order: **B is smallest + lowest-risk**
  (kibitzer `PolicyConsumer.from_db` already exists, so the workstream is essentially the
  conformance test + pointing lackpy at the same `policy.db`) **and** it's the safety-critical
  invariant — **do B first**. **C is larger than a flag** (a `connect()` signature + plumbing
  change, §2). **A is last** (net-new `RatchetConsumer` + the full-agent A/B; still wants C's
  cheap repeated reads first).
- **Gate per workstream:** T1 → T2 → T3; do not merge a workstream until its **T3 bar**
  clears, not just T1/T2.
- **Repos & commits:** fledgling (C), kibitzer + lackpy + umwelt (B), agent-riggs +
  kibitzer + lackpy (A). All signed; on snape (or longbottom with the 24h passphrase cache
  primed). Branch per workstream (`phase4/persistent-cache`, `phase4/policy-conformance`,
  `phase4/learn-loop`); each lands with its T1/T2 tests + a T3 report committed alongside.
- **Read-first:** kibitzer `umwelt/consumer.py` (the `PolicyConsumer` pattern B & A both
  reuse) and agent-riggs' `plugins/ratchet.py` (the `ratchet_decisions` schema = A's read
  contract). The lackpy `trace-log` worktree is producer-side (traces for ingest), **not** a
  consumer to reconcile with.

## 7. Why this is the foundation for the vision, not a detour

Each Phase 4 deliverable is the local, single-machine form of a goo-layer primitive
([vision/integrations/](./integrations/)):

| Phase 4 (here, now) | becomes (vision) |
|---|---|
| agent-riggs promoted-ratchet store, consumed in-session | `goo://activity/` — the uniform action stream agent-riggs learns from |
| one `.umw`, two enforcers (kibitzer + lackpy) | umwelt as goo dispatch middleware — one policy, every surface |
| persistent file-backed fact DuckDB | the `data` taxon / `goo://data/` resolvable, content-negotiable relations |

Close the loop on one machine first; the loop spoken over goo is the same loop with an
addressing layer. Phase 4 earns that horizon.

## 8. Open questions to settle before A starts

1. **Where does the ratchet consumer live** — kibitzer (coaching), lackpy (seeding), or
   both? (Determines the read contract's home.)
2. **Auto-promote vs human-in-the-loop** — *v1 decision (see §4): explicit `ratchet-promote`*,
   because it lowers false-promotion risk and lets T2 be deterministic. Revisit auto-promote
   only after the precision bar clears on the explicit path. (Listed here because it's the
   day-one decision the calibration pass must lock.)
3. **One project cache dir** — do `.bird` (blq), `.fledgling/cache.duckdb`, and
   `.umwelt/policy.db` consolidate under one `.retritis/`? (Ergonomics + gitignore.)
4. **umwelt's ratchet vs agent-riggs' ratchet** — umwelt proposes *policy views* from
   observations; riggs promotes *behavioral patterns*. Keep distinct in v1; a later tie-in
   (riggs observations → umwelt policy proposal) is Phase 4.5.
