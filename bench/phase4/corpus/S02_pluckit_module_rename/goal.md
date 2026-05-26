# S02 — module rename (`pluckit.plugins` → `pluckit.pluckins`)

**Archetype:** an upstream dep renamed a module; a downstream import still uses the
old path. pluckit 0.13 renamed `plugins` → `pluckins`; fledgling's e2e test still does
`from pluckit.plugins.viewer import AstViewer` → `ModuleNotFoundError`.

**Fixture:** fledgling @ pre-fix (`fixture.ref`).
**Goal:** resolve the import so the viewer e2e test passes (the module is `pluckins`).
**Success:** `tests/test_e2e_integration.py::TestPluckitViewer::test_view_functions` passes.
**Feeds:** A (a clean, real, single-edit failure).
