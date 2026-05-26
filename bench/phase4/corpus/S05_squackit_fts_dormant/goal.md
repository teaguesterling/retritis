# S05 — dormant feature (squackit FTS index never built → search returns empty)

**Archetype:** a feature silently no-ops because a prerequisite (the FTS index) was never
built. Before squackit's lazy-rebuild fix (commit ab16b82), `search_code` returned empty
ecosystem-wide.

**Status:** PENDING. Runnable once we have a squackit pre-FTS worktree *and* per-fixture
venv isolation — squackit's `search` runs through a console-script binary that won't honor
`PYTHONPATH=<fixture>` (unlike the fledgling pytest scenarios), so the editable install
would shadow the buggy fixture. See bench README "fixture isolation".
**Feeds:** C (FTS), A.
