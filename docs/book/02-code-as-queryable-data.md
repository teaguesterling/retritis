# 2. Code as Queryable Data

The premise that makes the whole suite cohere: a codebase is structured data that has
simply not been loaded into a database yet. Once you load it, "tools for understanding
code" become "queries," and queries are fast, composable, and exact.

## From text to tables

A traditional code search treats a repository as a pile of bytes. retritis treats it as
several tables:

- **definitions** — every function/class/method: name, kind, file, line span, signature.
- **calls / references** — the edges between them (who calls what).
- **fts.content** — a full-text index (BM25) over code identifiers, comments, strings, and
  markdown sections, so relevance ranking is possible.
- **git** — commits, diffs, blame, file history.
- **chat/sessions** — your own prior tool calls and conversations, indexed.

These come from parsing the source with **tree-sitter** (a real grammar, not regex), the
git object store, and the docs/log files — all materialized into **DuckDB**, an in-process
analytical database. The query engine is SQL.

> **Why DuckDB?** It is in-process (no server to run), columnar and fast for the
> scan-and-aggregate shape these queries take, and extensible — the suite leans on
> community extensions for AST extraction (`sitting_duck`), file reading (`read_lines`),
> markdown (`markdown`), and full-text search (`fts`). One engine answers code, docs,
> history, and chat questions with the same dialect.

## Why this beats grep for an agent

`grep "connect"` returns lines containing the substring — including comments, unrelated
identifiers, and the string "disconnect." A query over the definitions table returns the
*function named* `connect`, with its location and signature, and a join to the calls table
returns its callers. The difference is **precision and structure**: you get answers shaped
like the question, not lines you must then parse yourself.

It is also a matter of **cost**. grep re-reads the tree on every invocation. The DuckDB
index is built once; subsequent queries are scans of an in-memory (or memory-mapped) table.
At repo scale this is the difference between seconds and milliseconds — and the persistent
cache (Chapter 3) makes "built once" mean *once per content change*, not once per session.

## The cost that motivates the cache

Building the index is the expensive step: extracting the AST and creating the FTS index
over a whole tree can take a few seconds. Doing that on every `connect()` — every session,
every hook — is wasteful when the source hasn't changed. Workstream C of the suite's
Phase 4 made the DuckDB file-backed: a *builder* writes it once, *readers* attach it
read-only and skip the rebuild, and a **content key** (git HEAD plus uncommitted changes,
not mtime) decides when a rebuild is actually needed. Repeated queries dropped from ~4s to
~0.3s — an order of magnitude — purely by not rebuilding. Chapter 3 shows the mechanism.

## The lesson the suite keeps relearning

If the index is a contract between a producer (the parser) and consumers (the tools), then
*the shape of that data is an API*. Two episodes in the suite's history make the point:
squackit once reached into fledgling's private attributes and shattered whenever fledgling
refactored; lackpy once read a flat dict shape that the policy engine never actually
produced, and failed the moment it met a real database. Both are the same bug — a consumer
guessing at a producer's shape. The fix, both times, was to make the contract explicit and
test it from the producer side. Keep that in mind whenever you cross one of these seams.
