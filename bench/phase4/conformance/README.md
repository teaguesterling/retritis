# B conformance — one policy, two enforcers (skeleton)

Tests the workstream-B invariant (phase-4.md §3): a single `.umw` compiled to
`policy.db` must yield **identical** allow/deny verdicts from **kibitzer**
(`PolicyConsumer.from_db`), **lackpy** (`policy/sources/umwelt`), and the umwelt
`PolicyEngine` ground truth — **zero divergence** over a boundary-rich `(tool, path)`
corpus. Divergence is a *security* bug, not a nuisance.

- `policy_agreement.py` — `gen_cases` (real, runnable: `python policy_agreement.py`) +
  the three-way assertion. Verdict-getters: `truth`/`kibitzer` are written against the
  real APIs; `lackpy` is the explicit **workstream-B TODO**.
- `sample.umw` — the fixture policy.

**Pending workstream B:** there is no compiled `policy.db` yet, so `test_policy_agreement`
**skips**. B's work = `umwelt compile sample.umw -> .umwelt/policy.db`, point kibitzer +
lackpy at it (no reimplemented evaluator — both resolve through the same `PolicyEngine`),
then this test goes green at zero divergence.
