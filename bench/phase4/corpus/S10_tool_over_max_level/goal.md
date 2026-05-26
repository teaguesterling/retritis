# tool_over_max_level (B · policy conformance)

**Archetype:** one `.umw` policy, two enforcers. a level-4 tool requested under a max-level:2 cap must be DENIED

**Status:** PENDING — blocked on workstream **B** (compile `.umw` → policy.db; kibitzer
`PolicyConsumer.from_db` + lackpy `policy/sources/umwelt` read the SAME artifact).
This row is part of the **conformance corpus**: expected verdict = `deny`, and the
test asserts kibitzer == lackpy == umwelt PolicyEngine ground truth (zero divergence).
**Feeds:** B.
