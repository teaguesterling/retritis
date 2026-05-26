# S01 — API-drift compat break (`ToolInfo` subscript)

**Archetype:** an internal API changed (a return type became a dataclass) and a
downstream call site still subscripts it like a dict — the exact failure that broke
fledgling's `pro` server against pluckit 0.13 this session.

**Fixture:** `fledgling` at the pre-fix commit (`fixture.ref`). `fledgling/pro/server.py`
does `con._tools.list()` then `macro_info["name"]`, but `_tools.list()` now yields
`ToolInfo` dataclasses → `TypeError: 'ToolInfo' object is not subscriptable`, which
errors `create_server()` and cascades through every `test_pro_*` test.

**Goal (for the agent under test):** make the `pro`-server tests pass — find that
`ToolInfo` is a dataclass and use attribute access (`.macro_name` / `.params`).

**Success (`check.py`):** the discriminating pro test
`tests/test_pro_resources.py::TestResourcesWorkWithoutToolCalls::test_fresh_server_resources`
passes (it constructs a fresh server, which is exactly the code path that errors when
the bug is present).

**Feeds:** workstream **A** (a clean, real, repeatable failure to resolve — and, paired
with a seeded ratchet, the repeat-failure A/B) and **C** (the pro tests exercise repeated
fledgling connects, where the persistent cache should show up).
