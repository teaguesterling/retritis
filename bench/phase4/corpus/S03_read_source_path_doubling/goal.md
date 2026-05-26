# S03 — path-join bug (`read_source` doubles the repo root for git reads)

**Archetype:** a path is absolutized once, then a helper prepends the root again.
`read_source_text(commit=…)` calls `git_uri(_session_root(), file_path, …)` with an
already `_resolve()`'d absolute `file_path`, producing
`git:///…/fledgling/…/fledgling/sql/source.sql@HEAD`.

**Fixture:** fledgling @ pre-fix (`fixture.ref`).
**Goal:** make `read_source` with a `commit` read the file (relativize before `git_uri`).
**Success:** `tests/test_mcp_server.py::TestReadLines::test_reads_git_version` passes.
**Feeds:** A, C (the read path exercises repeated fledgling connects).
