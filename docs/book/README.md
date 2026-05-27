# Retritis: An Agent's Field Guide to the Suite

> *Code is data. Reach for a tool, not a shell.*

An O'Reilly-style guide to the **retritis** suite — a set of Model Context Protocol
(MCP) servers and libraries that turn a codebase into queryable data and give a coding
agent typed, indexed, policy-aware tools instead of raw `bash`.

This book is written for two readers at once:

- **The agent** working inside a repository that has the retritis plugins installed
  (Claude Code, or any MCP client). Start with the **Preface** — it gets you productive
  in one session and rewires the reflex from `grep | sed | cat` to the suite's tools.
- **The human** building, operating, or extending the suite. The chapters teach each
  component from first principles, with the design rationale and the seams between them.

## Table of contents

- **[Preface — Getting Your Agent Up and Running](00-preface.md)**  *(start here if you are the agent)*

### Part I — Foundations
- [1. The Suite at a Glance](01-suite-at-a-glance.md)
- [2. Code as Queryable Data](02-code-as-queryable-data.md)

### Part II — The Code-Intelligence Core
- [3. fledgling — SQL Macros over DuckDB](03-fledgling.md)
- [4. pluckit — CSS-over-AST](04-pluckit.md)
- [5. squackit — The Code-Intelligence Server](05-squackit.md)

### Part III — The Workflow Loop
- [6. blq — Build-Log Query](06-blq.md)
- [7. jetsam — Git, as a Workflow](07-jetsam.md)
- [8. kibitzer — Modes, Coaching, and Policy](08-kibitzer.md)

### Part IV — Generation, Memory, and Policy
- [9. lackpy — Intent to Program with Local Models](09-lackpy.md)
- [10. agent-riggs — Cross-Session Memory and Ratchets](10-agent-riggs.md)
- [11. umwelt — Policy as a Cascade](11-umwelt.md)
- [12. nsjail — Sandboxed Execution](12-nsjail.md)

### Appendices
- [A. The bash → suite cheat sheet](A-cheatsheet.md)
- [B. Per-server tool reference](B-tool-reference.md)

## Status & direction

This guide describes the **shipped** suite — what you use today. The architecture is
actively evolving; for the *proposed* revisions (splitting lackpy into language/runtime/
generator, kibitzer's explicit enforce/coach faculties, umwelt as an opt-in
event-in-context rule engine, agent-riggs as umwelt's rule *generator*) see
[RFC 0001 — Suite architecture](../rfcs/0001-suite-architecture.md). Where this guide and
the RFC differ, the guide is *now* and the RFC is *next*.

## Conventions

- **Agent Recipe** callouts give a copy-pasteable tool-first way to do a common task.
- **Why, not just how** sidebars explain a design decision so you can extend it.
- Tool names use their MCP form, e.g. `squackit.search_code`, `fledgling.FindCode`,
  `blq.run`. In a client they appear namespaced (`mcp__plugin_squackit_squackit__search_code`).
