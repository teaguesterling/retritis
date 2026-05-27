# Appendix B — Per-server tool reference

The MCP tool surface by server. Names are the bare tool; clients show them namespaced
(`mcp__plugin_<server>_<server>__<tool>`). For exact arguments, call each server's own
help (`squackit.help`, `fledgling.Help`, `blq.commands`, `lackpy.language_spec`).

## squackit — code intelligence
- **Search/rank:** `search`, `search_code`, `search_content`, `search_docs`, `search_chat`,
  `search_messages`, `find`, `find_names`, `find_code_ranked`
- **Navigate/understand:** `investigate`, `call_graph`, `explore`, `project_overview`,
  `complexity`, `changed_function_summary`, `doc_outline`
- **Read:** `read_source`, `read_context`, `view`, `read_doc_section`, `list_files`,
  `file_at_version`
- **Diff/history:** `working_tree_status`, `file_diff`, `structural_diff`, `file_changes`,
  `recent_changes`, `branch_list`, `tag_list`
- **Sessions/chat:** `sessions`, `session_detail`, `browse_sessions`, `messages`,
  `tool_calls`, `browse_tool_usage`
- **Low-level/meta:** `ast_select_from`, `pluck`, `dr_fledgling`, `fts_stats`, `help`

## fledgling — SQL/DuckDB engine
- **Code:** `FindCode`, `FindDefinitions`, `SearchCode`, `SearchContent`, `SearchProject`,
  `SelectCode`, `ViewCode`, `ReadLines`, `CodeStructure`, `ExploreProject`,
  `InvestigateSymbol`
- **Docs:** `SearchDocs`, `MDOverview`, `MDSection`
- **Git:** `GitDiffFile`, `GitDiffSummary`, `GitShow`, `ReviewChanges`
- **Chat:** `ChatSearch`, `ChatDetail`, `ChatSessions`, `ChatToolUsage`
- **FTS/meta/SQL:** `FtsStats`, `Help`, `describe`, `list_tables`, `query`

## blq — build-log query
- **Run/inspect:** `run`, `exec`, `status`, `errors`, `output`, `info`, `inspect`, `query`
- **History/report:** `history`, `events`, `report`, `diff`
- **Commands:** `commands`, `register_command`, `unregister_command`
- **CI/sandbox:** `ci_generate`, `ci_check`, `clean`, `sandbox_info`

## jetsam — git workflow
- **Read:** `status`, `log`, `diff`, `show_plan`, `checks`, `issues`, `pr_list`, `pr_view`,
  `pr_comments`
- **Mutating (→ `confirm`):** `save`, `sync`, `start`, `finish`, `ship`, `release`,
  `switch`, `tidy`, `modify_plan`, `issue_close`, `pr_comment`, `pr_review`, `cancel`
- **Confirm/escape:** `confirm`, `git`

## kibitzer — modes, coaching, policy
- `ChangeToolMode`, `GetFeedback`, `GetDocContext`
- *(modes: free, implement, test, docs, explore, review)*

## lackpy — intent→program
- **Generate/run:** `generate`, `create`, `run_program`, `delegate`, `validate`
- **Kits/toolboxes:** `kit_list`, `kit_info`, `kit_create`, `toolbox_list`
- **Docs/config:** `language_spec`, `docs_index`, `resolve_doc`, `provider_list`, `config`

## agent-riggs — memory (CLI)
- `agent-riggs ingest` · `agent-riggs ratchet promote|reject|history <key>`
- store: `.riggs/store.duckdb` (tables: `turns`, `failure_stream`, `ratchet_decisions`)

## umwelt — policy (library/CLI)
- `PolicyEngine.from_files(world, stylesheet)` → `.save(db)`; `.from_db(db)`;
  `.resolve(type, id, property=, context={"mode":…})`, `.resolve_all(type, context=)`,
  `.trace(...)`
