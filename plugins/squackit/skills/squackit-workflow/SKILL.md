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

### Find things
- `find_names(pattern, type?)` — definitions by name pattern + node type (`.fn`, `.cls`, `.var`)
- `find_definitions(symbol)` — cross-file symbol resolution
- `find_callers(symbol)` — who calls / references this
- `find(query)` — generic structural finder (selector syntax)
- `find_code_ranked(query)` — ranked code search with relevance scoring
- `find_names(query)` — name-pattern matching

### Read things
- `read_source(path, range?)` — read a file or range
- `read_context(symbol)` — read the *contextual* code around a symbol (smarter than line-range reads)
- `read_doc_section(path, heading)` — pull a section from a markdown doc

### Understand structure
- `code_structure(path)` — file/module hierarchy with depth control
- `project_overview()` — top-level project shape
- `complexity(path)` — complexity hotspots
- `call_graph(symbol)` — call relationships
- `explore(path)` — interactive structural exploration
- `investigate(symbol)` — deep dive on a symbol (definitions + callers + structure in one)

### Search across content (FTS)
- `search(query)` — full-text search across the project
- `search_code(query)` — code-aware search
- `search_content(query)` — content-aware search (incl. comments + docstrings)
- `search_docs(query)` — search documentation
- `search_chat(query)` — search past Claude session transcripts (forwards to fledgling)
- `search_messages(query)` — message-level chat search

### Browse activity
- `list_files(pattern)` — file listing with smart filters
- `recent_changes()` — recent commits / changes
- `file_changes(path)` — change history of a single file
- `file_at_version(path, ref)` — read file at a git revision (forwards to fledgling)
- `file_diff(path, from, to)` — file-level diff between revisions
- `structural_diff(from, to)` — function-level structural diff
- `changed_function_summary(from, to)` — summary of functions that changed
- `branch_list()` / `tag_list()` / `working_tree_status()` — git state queries

### Help + diagnostics
- `help()` — list available tools
- `dr_fledgling()` — diagnose fledgling backend health
- `fts_stats()` — FTS index health

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
