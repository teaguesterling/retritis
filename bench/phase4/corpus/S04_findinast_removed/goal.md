# S04 — stale test after a tool was renamed/removed (`FindInAST` → `FindCode`)

**Archetype:** a tool was intentionally removed (`FindInAST` → `FindCode`/`SelectCode`,
per `sql/tools/code.sql`), but the test suite still calls the old tool name and gets
"Tool not found".

**Fixture:** fledgling @ pre-fix (`fixture.ref`).
**Goal:** point the AST-find tests at the current tool (`FindCode`).
**Success:** `tests/test_mcp_server.py::TestFindCode::test_finds_calls` passes (this node
does not exist on the buggy fixture, where only `TestFindInAST` exists → check fails as the
correct baseline; on the fixed tree the retargeted test passes).
**Feeds:** A.
