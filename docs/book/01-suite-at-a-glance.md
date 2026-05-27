# 1. The Suite at a Glance

retritis is not one tool; it is a *suite* whose pieces share two ideas — **code as
queryable data** and **the Model Context Protocol (MCP)** — and otherwise do one job each,
well. This chapter is the map. Each later chapter is a tool.

## The components

| Tool | One line | Layer |
|---|---|---|
| **fledgling** | SQL macros over a DuckDB-parsed AST + full-text index | engine |
| **pluckit** | a CSS-like selector language over the AST | engine |
| **squackit** | the code-intelligence MCP server the agent actually calls | interface |
| **blq** | run builds/tests and *query* their captured logs | workflow |
| **jetsam** | git as a confirmable workflow, not raw plumbing | workflow |
| **kibitzer** | modes, coaching hooks, and policy enforcement for the agent | governance |
| **umwelt** | author policy as a CSS-like cascade, compile it to a database | governance |
| **lackpy** | turn natural-language intent into a restricted, runnable program | generation |
| **agent-riggs** | learn across sessions: turns, trust, promoted "ratchets" | memory |
| **nsjail** | sandbox untrusted execution | safety |

## The two unifying ideas

**Code as queryable data.** Parsing source into an AST and loading it (plus git history,
docs, and chat logs) into DuckDB means every question about the code is a *query*, not a
file walk. "Find the definition," "who calls this," "what changed structurally," "rank
these matches" all become SQL over typed tables — fast because the index is built once and
reused. fledgling provides the engine; pluckit provides a friendlier selector syntax;
squackit packages the useful queries as tools. (Chapter 2 develops this.)

**MCP everywhere.** Each capability is exposed as an MCP server, so any compatible agent
gets the tools without bespoke glue. The servers are independent processes with a small,
typed tool surface — which is why the suite composes and why a missing server degrades
gracefully instead of breaking the others.

## How data flows

```
 source tree ─► tree-sitter AST ─┐
 git history ───────────────────┤─► DuckDB (fledgling)  ◄── pluckit selectors
 docs (markdown) ───────────────┤        │
 chat/session logs ─────────────┘        ▼
                                squackit tools  ─────►  the agent
 build/test runs ─► blq DuckDB (.bird) ─►  the agent
 policy (.umw) ─► umwelt ─► policy.db ─► kibitzer (enforces) / lackpy (restricts)
 session turns ─► agent-riggs (.riggs) ─► promoted ratchets ─► kibitzer (surfaces)
```

The recurring shape: a producer parses something into a DuckDB file; a consumer reads it.
That seam — *the schema is the contract* — is deliberate, and it is where the suite's
versioning discipline lives (Chapters 3, 8, 10, 11).

## Reading order

If you are the agent, you already read the Preface; come back here when a tool surprises
you. If you are building or operating the suite, read straight through: Part I (this and
the next chapter) gives the philosophy, Part II the engine and the agent's main interface,
Part III the verify/persist/govern loop, Part IV generation, memory, and policy.
