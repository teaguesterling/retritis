# 3. fledgling — SQL Macros over DuckDB

fledgling is the engine. It connects to DuckDB, loads the extensions and a library of
**SQL macros**, and exposes code/doc/git/chat intelligence as callable queries. squackit
is built on it; you can also use it directly (notebook, script, or its own MCP server).

## The mental model

A fledgling `Connection` is a DuckDB connection with a curated set of macros attached.
A macro is a named, parameterized SQL query — `find_definitions('**/*.py')`,
`search_content('connect')`, `recent_changes(5)` — that reads the AST/FTS/git tables. You
call macros; fledgling runs SQL. That is the whole idea: **the API is a query library.**

```python
import fledgling
con = fledgling.connect(root="/path/to/project")   # parse + load macros + extensions
con.search_content("connect").limit(5).df()        # a macro, returning a DuckDB relation
con.con.execute("SELECT * FROM search_content('connect') LIMIT 5").fetchall()  # or raw SQL
```

## The public connection contract

Downstream tools (pluckit, squackit) used to reach into fledgling's *private* internals
(`._con`, `._tools`) and broke on every refactor. As of **0.10** there is a documented,
SemVer-stable surface:

- `Connection.con` → the raw `duckdb.DuckDBPyConnection` (was `._con`).
- `Connection.tools` → the `Tools` registry; `Tools.list()` returns `ToolInfo` dataclasses
  describing each user-facing macro (name, params).
- `Connection.ensure_fts()` → idempotent: builds the `fts.content` index on first use, or
  if empty; a no-op thereafter.

> **Why this matters.** The schema and these accessors are the contract between fledgling
> and everything above it. Consumers depend on `con.con`/`con.tools`/`ensure_fts()`, not on
> attributes that might be renamed. If you extend fledgling, add to this surface
> deliberately; don't make downstreams guess.

## Loading: `connect()`, `configure()`, profiles

`connect(init=None, root=None, profile="analyst", modules=None, extensions=True, persist=None, read_only=False)`:

- **Modes.** `init='path'` runs an explicit init file; `init=None` auto-discovers sources
  plus a project-local `.fledgling-init.sql` overlay; `init=False` loads sources only.
- **profile** (`analyst` vs `core`) selects the macro/lockdown posture. `lockdown()` can
  pin `allowed_directories` and disable external access for a hardened connection.
- **extensions** loads the DuckDB extensions fledgling's macros need (`read_lines`,
  `sitting_duck`, `markdown`, `duck_tails`, `fts`). On a read-only reader they auto-load
  on demand, so only what a query touches is paid for.

## Full-text search

`ensure_fts()` builds a BM25 index (`fts.content`) over markdown sections, code
definitions, comments, and string literals. `search_content`/`search_docs`/`search_code`
query it; `FtsStats` reports its size. FTS is what makes results *ranked* rather than
filesystem-ordered — the single biggest quality win over grep.

## The persistent cache (0.11)

By default the DuckDB is in-memory and rebuilt every `connect()` — a ~4s cost dominated by
AST extraction + FTS index creation. fledgling 0.11 makes it file-backed:

- `connect(persist="<path>", read_only=<bool>)` — with `persist`, the macros, tables, and
  FTS index live in the file. A **read-only** reader issues no catalog writes (the macros
  are already persisted, so `configure()` is skipped) and loads only the query extension on
  demand — a cache-hit `connect()` is ~tens of ms.
- `build_cache(persist, root, *, force=False)` — the single-writer builder. It is
  idempotent and **staleness-aware**: it rebuilds only when the project content key has
  changed, otherwise returns `False`.
- `cache_is_fresh(persist, root)` — a read-only freshness probe.

The **content key** is `git HEAD + uncommitted (tracked) changes`, *not* mtime — because a
fresh `git worktree` checkout has new mtimes but identical content, and an mtime key would
force needless rebuilds. The cache file and its sidecars are excluded from the key so the
cache can't invalidate itself.

> **Agent Recipe — the cheap-read pattern.** A builder process (or the first query of the
> day) calls `build_cache(path, root)`; every reader opens
> `connect(persist=path, read_only=True)` and queries. The build is paid once per content
> change; reads are near-free. This is what makes per-hook code-context affordable.

Two performance details worth knowing because they generalize: constructing a `Connection`
used to eagerly run tool **discovery** (an `mcp_list_tools()` + catalog scan, ~80ms) —
now lazy, so a reader that only queries never pays it; and the `fts` extension is **not**
eager-loaded on read — DuckDB autoloads it on the first `match_bm25` query, so a non-FTS
reader pays nothing. The theme: a reader should pay only for what it touches.

## Pinning note

fledgling pins `duckdb==1.5.2`: the community extensions it depends on are published for
1.5.2, and an unbounded `duckdb>=1.5.0` would pull 1.5.3, whose extensions aren't available
— breaking FTS on a fresh install. If you bump duckdb, the extensions must be rebuilt for
the new version first.
