# B conformance — one policy, two enforcers

The workstream-B invariant (phase-4.md §3): a single umwelt policy, compiled once to
`policy.db`, must yield **identical** verdicts from every independent reader.
Divergence is a *security* bug — the agent would be sandboxed differently than it
believes.

## The policy (one source of truth)
- `world.yml` — the entities (tools Read/Grep/Edit/Write/Bash·dangerous; modes
  implement/review/explore).
- `policy.umw` — the cascade: unscoped + per-tool permission/constraints, mode
  properties (writable/strategy/coaching-frequency), and mode-scoped tool gating.

`PolicyEngine.from_files(world, stylesheet).save(policy.db)` compiles them. The test
builds this in a tmp dir automatically (or honors `PHASE4_POLICY_DB` if you point it at
a pre-compiled db).

## The three readers
| reader   | how it reads | granularity |
|----------|--------------|-------------|
| **truth**    | `PolicyEngine.resolve` | everything |
| **kibitzer** | `PolicyConsumer.from_db` (the hook's own path) | (tool, path, **active_mode**) |
| **lackpy**   | `policy.sources.umwelt.UmweltPolicySource` | tool **set** + constraints, **no mode/path** |

## What B found
Running this harness against lackpy as shipped fails immediately:
`UmweltPolicySource.resolve` does `name = entry["id"]`, but umwelt's real
`resolve_all(type="tool")` returns `{entity_id, properties:{allow, max-level,
allow-patterns, deny-patterns}}` — nested, hyphenated, and keyed `entity_id`, with
`allow` (not `visible`). lackpy had **only ever been tested against a flat-dict stub**
(`tests/policy/test_umwelt_source.py::FakePolicyEngine`), so it had never read a real
compiled policy. → `KeyError: 'id'`. The fix migrates the source to the real shape
(incl. splitting comma-separated pattern strings); see lackpy commit.

## Tests
- `test_tool_allow_three_way` / `test_constraints_three_way` — **the gate**:
  truth == kibitzer == lackpy on the unscoped allow verdict + (max-level, patterns).
- `test_mode_scoped_tool_allow_kibitzer_vs_truth` / `test_mode_policy_kibitzer_vs_truth`
  — the mode dimension, where only the two mode-aware readers participate.
- `test_lackpy_is_mode_unaware` — **records the finding** that lackpy's `PolicyContext`
  has no `mode` field, so mode-scoped policy is invisible to it. The test fails if a
  future lackpy adds mode (a signal to widen the three-way gate), so the scoping is
  never a silent accident.

Run: `python -m pytest policy_agreement.py -q`  (or `python policy_agreement.py` for a
`gen_cases` demo).
