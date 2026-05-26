# S07 — FTS index build cost (workstream C baseline)

**Archetype:** the pure cost workstream C eliminates — connect + `rebuild_fts`, no query.
This is what a file-backed cache turns into an attach instead of a ~2s rebuild per process.

**Goal/metric:** baseline the index-build latency. `check` succeeds when the FTS table is
non-empty; `latency_ms` is the signal C must beat.
**Feeds:** C (latency).
