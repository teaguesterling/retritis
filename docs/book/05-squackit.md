# 5. squackit — The Code-Intelligence Server

squackit is the server you, the agent, actually call. It composes fledgling (SQL/DuckDB)
and pluckit (CSS-over-AST) into a broad, high-level MCP tool surface for understanding a
codebase — search, navigation, reading, structural diffing, and session/chat recall. If
the Preface's reflex table sent you somewhere, it usually sent you here.

## Tool families

squackit's tools group into a handful of jobs. (Exact arguments: call `squackit.help`.)

- **Search & rank.** `search`, `search_code`, `search_content`, `find`, `find_names`,
  `find_code_ranked`, `search_docs`, `search_chat`, `search_messages`. Use
  `find_code_ranked` when you want the *best* matches, not all of them.
- **Navigate & understand.** `investigate` (a dossier on a symbol — definition, callers,
  complexity), `call_graph`, `explore`, `project_overview`, `complexity`,
  `changed_function_summary`, `doc_outline`.
- **Read precisely.** `read_source`, `read_context`, `view`, `read_doc_section`,
  `list_files`, `file_at_version`. Read the *range a query pointed you at*, not whole files.
- **Diff & history.** `working_tree_status`, `file_diff`, `structural_diff` (what changed
  *structurally*, not just textually), `file_changes`, `recent_changes`, `branch_list`,
  `tag_list`.
- **Sessions & chat.** `sessions`, `session_detail`, `browse_sessions`, `messages`,
  `tool_calls`, `browse_tool_usage` — your own history, queryable.
- **Lower-level.** `ast_select_from` (run a pluckit selector), `pluck`, `read_source`,
  `dr_fledgling` (a fledgling health check), `fts_stats`, `help`.

> **Agent Recipe — "understand this symbol before you change it."**
> `squackit.investigate("FunctionName")` → definition + callers + complexity in one call.
> Then `squackit.read_source` the exact span. You now know the blast radius without having
> grepped for callers or opened a file.

> **Agent Recipe — "what did my last change actually do?"**
> `squackit.working_tree_status` → `squackit.structural_diff` (functions added/removed/
> changed, not just lines). This catches "I edited the right text in the wrong place" that
> a textual diff hides.

## Built on a contract

squackit is a *consumer* of fledgling and pluckit. It reads `con.con`/`con.tools`,
`plucker.pluckins`, `Chain.MUTATION_OPS` — the public surfaces from Chapters 3–4 — and
declares compatible version pins (`fledgling-mcp>=0.10`, `ast-pluckit>=0.13`). This is the
payoff of the public-contract work: squackit composes the engine by a versioned API, so a
fledgling refactor no longer shatters it.

## When to use squackit vs fledgling directly

Use **squackit** for everything the packaged tools cover — which is almost all day-to-day
code intelligence. Drop to **fledgling** (raw macros / SQL) only when you need a query
squackit doesn't expose, or you're embedding the engine in your own script. Think of
squackit as the standard library and fledgling as the language underneath.
