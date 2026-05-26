# repeat_path_doubling (A · repeat-failure A/B)

**Archetype:** a failure seen once should resolve faster the second time. Seed the ratchet
store from `S03_read_source_path_doubling`, FREEZE it, then re-encounter the same failure in a fresh session;
kibitzer should surface the recorded fix.

**Status:** PENDING — blocked on workstream **A** (RatchetConsumer reading promoted ratchets
in-session). S15 is the **control**: a genuinely new break with no seeded ratchet, to bound
false-promotion (the loop must NOT surface an unrelated fix).
**Feeds:** A (the headline cost A/B: turns/tokens on repeats; adoption; false-promotion).
