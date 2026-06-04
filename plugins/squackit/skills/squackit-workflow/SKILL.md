---
name: squackit-workflow
description: Code intelligence — the wrapper-layer over fledgling for everyday code search and structural understanding. Triggers on "find X in the code", "where is X defined", "show me what calls X", "what's the structure of this project", "outline this file/module", "what does X look like". USE THIS FIRST for any "find/where/who-calls/show-structure" question in source — squackit handles FTS, AST queries, caching, and per-root context that grep/find can't. Fall through to fledgling-workflow only for git diff/revision reads or Claude conversation history that squackit doesn't expose. NOT raw `grep -r`/`find -name`/`rg` via Bash — those skip the AST + FTS index that's the whole point.
version: 1.0.0
---

# squackit — code intelligence (the fledgling wrapper)

squackit is a higher-level code-search and code-structure layer built over
fledgling. For everyday "find this / where is this / what's the shape of this"
questions, reach for squackit FIRST. It handles:

- FTS-indexed text search across the project
- AST-based definition / reference / caller lookup
- Hierarchical code structure (file → class → method)
- Per-root session caching (repeated queries are fast)
- Token-aware result truncation that fits your context window

It uses fledgling's primitives underneath, so you get the same accuracy as
direct fledgling calls without the boilerplate of constructing AST queries by
hand.

## When to use squackit vs raw search

Do NOT run `grep -r` / `find -name` / `rg` through Bash for code questions.
Use these squackit MCP tools:

| Instead of... | Use squackit |
|---|---|
| `grep -r "def foo"` / `grep -r "class Bar"` | `find_names` with name pattern + node-type selector |
| `grep -rn "import X"` then trace usages | `find_callers` for direct caller resolution |
| Multiple greps to find where a symbol is *defined* (not just mentioned) | `find_definitions` (cross-file, AST-aware) |
| Reading entire files to understand structure | `code_structure` (hierarchical, depth-controlled) |
| Reading the whole project to orient | `project_overview` |
| `grep -rl` to find files matching a pattern | `find` with structural selectors |
| Reading a doc file front-to-back | `doc_outline` / `read_doc_section` |

## Core tools

### Find things by AST selector
- `find_names(source, selector, max_results?)` — names of AST nodes matching CSS selectors. `source` is a file/glob pattern (REQUIRED), `selector` is CSS-like (`.fn`, `.cls#name`, `.fn:has(.call#execute)`). For "find the function named X" use `find_names(source="**/*.py", selector=".fn#X")`. For "find all classes" use `selector=".cls"`.
- `find(source, selector, max_results?)` — AST nodes + file paths + line ranges. Same selectors as `find_names`.
- `find_code_ranked(selector?, fts_query?, file_pattern?, lang?, max_results?)` — code matches ranked by BM25 relevance.
- `ast_select_from(source, selector)` — raw AST selector query (lower-level than `find`).
- `view(source, selector, max_results?)` — render matching source as markdown with file:range headings + fenced code blocks.

### Read things
- `read_source(file_path, lines?, ctx?, match?, max_lines?)` — read lines with range/context/match filtering.
- `read_context(file_path, center_line, ctx?, max_lines?)` — read lines centered around a specific line.
- `read_doc_section(file_path, target_id, max_lines?)` — pull a markdown section by id (use `doc_outline` to find ids).

### Understand structure
- `project_overview(root?)` — file counts by language for the project.
- `explore(path?)` — first-contact briefing: languages, key defs, docs, recent activity.
- `investigate(name, file_pattern?)` — deep dive on a function or symbol: definition + source + callers + callees.
- `complexity(source, selector, max_results?)` — AST nodes matching selector, ranked by complexity. `source` + `selector` required, NOT a path.
- `call_graph(file_pattern?)` — call relationships within a file pattern (NOT a single symbol).

### Search across content (FTS)
- `search(query, file_pattern?)` — multi-source: definitions + call sites + docs in one call.
- `search_code(query, filter_kind?, root?, ...)` — BM25 over definitions + comments + string literals.
- `search_content(query, filter_kind?, filter_extractor?, root?, ...)` — BM25 across all indexed content.
- `search_docs(query, root?, ...)` — BM25 over markdown documentation sections.
- `search_chat(query, role?, project?, days?, lim?)` — search past Claude session transcripts.
- `search_messages(search_term)` — message-level chat search.
- `doc_outline(file_pattern?, search?, max_lvl?, max_results?)` — markdown section outlines with optional keyword filter.
- `fts_stats()` — FTS index health.

### Pluckit chain queries (advanced selector composition)
- `pluck(argv, allow_mutations?)` — whitespace-separated chain: `source_pattern [method [arg]]... [terminal]`. Terminals: `names | count | text | materialize | view | complexity`. Use `reset` to start fresh. Example: `**/*.py find .fn containing cache names`. Mutations blocked unless `allow_mutations=true`.

### Browse activity
- `list_files(pattern?, commit?, max_results?)` — files by glob, optionally at a git commit.
- `recent_changes(repo?, n?, max_results?)` — git commit history.
- `file_changes(repo?, from_rev?, to_rev?, max_results?)` — files changed between two revisions.
- `file_at_version(file, rev, repo?, max_lines?)` — file content at a git revision.
- `file_diff(file, from_rev?, to_rev?, repo?, max_lines?)` — line-level unified diff between revisions.
- `structural_diff(file?, from_rev?, to_rev?, repo?, max_results?)` — semantic diff: added/removed/modified definitions.
- `changed_function_summary(from_rev?, to_rev?, file_pattern?, repo?, max_results?)` — changed functions ranked by complexity.
- `review(from_rev?, to_rev?, file_pattern?)` — code review prep: changed files + top functions + diffs in one call.
- `branch_list(repo?, max_results?)` — git branches.
- `tag_list(repo?, max_results?)` — git tags.
- `working_tree_status(repo?)` — untracked + modified files.

### Claude session history (forwards to fledgling)
- `sessions()` / `session_detail(sid)` / `messages()` / `tool_calls()` — session metadata + tool-call history.
- `browse_sessions(project?, days?, lim?)` / `browse_tool_usage(project?, session_id?, days?, lim?)` — paginated browsing.

### Help + diagnostics
- `help(target_id?)` — skill guide outline (no args) or section detail (with id). Returns fledgling's skill guide.
- `dr_fledgling()` — diagnose the fledgling backend.

## Per-root opt-in

squackit caches per project root. To query a different repo:
- Most search tools accept `root=<dir>` to FTS that repo (LRU-cached)
- The cache stays warm during a session — repeated queries in the same root are cheap

## Tips

- For "what's in this codebase?" → `project_overview` then drill with `code_structure`
- For "find the function that does X" → `find_names("X")` or `find(".fn#X")` selector
- For "trace this bug" → `investigate(symbol)` then `find_callers(symbol)`
- For "what changed recently?" → `recent_changes()` or `file_changes(path)`
- For "how is this function actually used?" → `find_callers` not grep
- Results are token-aware — adjust depth/limit if you need more detail
