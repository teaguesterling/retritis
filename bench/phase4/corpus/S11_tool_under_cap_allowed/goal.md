# tool_under_cap_allowed (B · policy conformance)

**Archetype:** one `.umw` policy, two enforcers. a level-2 tool under a max-level:2 cap must be ALLOWED

**Status:** PENDING — blocked on workstream **B** (compile `.umw` → policy.db; kibitzer
`PolicyConsumer.from_db` + lackpy `policy/sources/umwelt` read the SAME artifact).
This row is part of the **conformance corpus**: expected verdict = `allow`, and the
test asserts kibitzer == lackpy == umwelt PolicyEngine ground truth (zero divergence).
**Feeds:** B.
