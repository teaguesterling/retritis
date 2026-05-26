# policy_out_of_scope_denied (B · policy conformance)

**Archetype:** one `.umw` policy, two enforcers. an edit to src/auth/** in the wrong mode must be DENIED by both kibitzer and lackpy

**Status:** PENDING — blocked on workstream **B** (compile `.umw` → policy.db; kibitzer
`PolicyConsumer.from_db` + lackpy `policy/sources/umwelt` read the SAME artifact).
This row is part of the **conformance corpus**: expected verdict = `deny`, and the
test asserts kibitzer == lackpy == umwelt PolicyEngine ground truth (zero divergence).
**Feeds:** B.
