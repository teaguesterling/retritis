# 10. agent-riggs — Cross-Session Memory and Ratchets

agent-riggs is the suite's long memory. It ingests what happened in your sessions — tool
calls, failures, trust over time — into a DuckDB store (`.riggs/store.duckdb`) and lets
good lessons be *promoted* into "ratchets" that a future session can act on. It is the
producer side of the "learn" step; kibitzer is the consumer.

## What it records

- **turns** — per tool-call signals: tool, success, mode, and a **trust score** smoothed by
  three EWMAs (`trust_1` now, `trust_5` session, `trust_15` baseline; e.g. α=0.4/0.08/0.02).
  Trust is how riggs notices things getting better or worse over time.
- **failure_stream** — failures with a category, tool, mode, and the trust at failure.
- **ratchet_decisions** — candidate fixes and their disposition.

`agent-riggs ingest` pulls session data in; the trust EWMAs update automatically.

## Ratchets: promotion is the gate

A **ratchet** is a recorded pattern-and-fix. Candidates are derived from the failure stream
(`find_constraint_candidates`) or recurring tool patterns; each has a `candidate_key` and an
`evidence` payload (occurrences, sessions, severity, or success-rate). A candidate becomes a
**ratchet** only when *promoted* — and promotion is **explicit and manual**
(`agent-riggs ratchet promote <key>` / `reject <key>`), recorded as `decision='promoted'`.

> **Why manual promotion.** A wrong suggestion is worse than none — it teaches the agent a
> bad reflex. Making promotion a deliberate human-in-the-loop act (rather than an automatic
> trust threshold) keeps the false-promotion rate down. Trust lives in the `turns` table and
> informs the human's decision; it is not, by itself, the promote trigger.

## The consumer contract

A `RatchetConsumer` (in kibitzer) reads the *promoted* rows read-only and matches them to a
**failure fingerprint**. The match key mirrors riggs's own derivation —
`f"{category}-{tool or 'unknown'}-{mode or 'any'}"` for constraint ratchets — so the
consumer must compute the key *identically* to the producer or it silently matches nothing.

> **The contract is the schema.** This is the same lesson as fledgling↔squackit: a consumer
> that guesses the producer's key format breaks silently. The suite pins it with a
> *producer-driven* conformance test — it drives the real `find_constraint_candidates` +
> `promote`, then asserts the consumer computes the same key. If you change how
> `candidate_key` is formed in riggs, that test goes red. Keep them in lockstep.

## The loop it closes

A failure observed in session N becomes a candidate; a human promotes the good ones; in
session N+1 kibitzer surfaces the recorded fix when the same fingerprint recurs — so the
agent resolves a repeat failure faster than it did the first time. That is the whole point
of "learn": not within a session (kibitzer does that) but *across* them.
