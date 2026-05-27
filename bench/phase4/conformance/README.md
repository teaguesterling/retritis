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

## The B finding — surfaced, then resolved (option C)

Fixing lackpy's shape bug exposed a deeper divergence: lackpy's `UmweltPolicySource`
was **mode-blind** — `PolicyContext` had no `mode`, and the source resolved the tool set
with no context, so mode-gated `allow:false` rules competed and lackpy **denied
Edit/Write/Bash in every mode** (incl. `implement`), while truth + kibitzer allowed them.
That was a design decision, not a silent fix, so it was surfaced. Teague chose **C —
thread the active mode through `PolicyContext`** (the architecturally correct option).

Implemented in lackpy `main`:
- `PolicyContext` gains a `mode` field.
- `UmweltPolicySource.resolve` reads `context.get("mode")` and threads it into
  `resolve_all(type="tool", context={"mode": mode})`; with no mode it passes an empty
  context = the **unscoped baseline** (rather than letting every mode's rules compete).
- `service.py` populates `policy_context["mode"]` from the kibitzer session's active
  `.mode`, so generation resolves the policy for the mode the agent is actually in.

Result: lackpy is now in the **three-way gate across every mode**. All tests pass, no
xfails:
- `test_tool_allow_three_way` / `test_constraints_three_way` — truth == kibitzer ==
  lackpy on every (mode, tool) allow verdict + constraints (incl. Bash's max-level
  tightening to 3 in implement).
- `test_mode_policy_kibitzer_vs_truth` — ModePolicy (writable/strategy/coaching) matches.
- `test_lackpy_is_mode_aware` — regression guard: the `mode` field must stay, and lackpy
  must allow Edit/Write/Bash in implement (so the mode-blind bug can't silently return).

> Aside (out of scope): lackpy's *broader* test suite is ~164-failing against the
> installed kibitzer (e.g. `KibitzerPolicySource` calls `KibitzerSession.has_coaching()`,
> which the installed kibitzer no longer exposes). That's the same drift class B targets,
> on the kibitzer-*hints* source rather than the umwelt-*policy* source — a separate
> follow-up.
