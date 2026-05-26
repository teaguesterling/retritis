# S06 — cold FTS search latency (workstream C baseline)

**Archetype:** the first content search in a session pays the full index build. Measures
connect + `rebuild_fts` + `search_content` against the fixture as a target codebase.
The fledgling code is the installed one; the fixture is just a corpus to index (the
pro-server bug at this ref doesn't affect FTS).

**Goal/metric:** baseline the COLD search latency that the persistent substrate (C) should
collapse to a cache hit. `check` succeeds when hits are found; `latency_ms` is the signal.
**Feeds:** C (latency).
