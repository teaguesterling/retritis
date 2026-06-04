---
name: fledgling-workflow
description: Code intelligence primitives — AST-based search, git diff/show, Claude conversation history. Triggers on "find this function/class", "what does this look like at HEAD~3", "diff between revisions", "search past sessions", "complexity hotspots", "module dependencies". PREFER squackit-workflow first for everyday code-search ("find/where is/show me X" in source) — squackit is a higher-level wrapper over fledgling that handles FTS+caching. Fall through to fledgling here when squackit doesn't cover the query: git revision reads (GitShow), cross-revision diffs (GitDiffSummary/GitDiffFile), Claude session history (ChatSearch/ChatSessions/ChatToolUsage), or direct SQL via `query` for complexity/dependency/structural-diff macros. NOT raw `grep`/`git log`/`git diff` via Bash — those bypass the AST + indexed history that's the whole point.
version: 1.0.0
---

# Fledgling — DuckDB Code Analysis

Fledgling provides AST-based code analysis, git diff tools, and conversation
history through DuckDB. Use fledgling tools for structural code understanding
instead of grep.

## When to use fledgling vs grep/git

- **First-contact briefing on an unfamiliar repo** → `ExploreProject` (one call: languages + top-complexity defs + doc outline + recent activity)
- **Find function/class definitions by name** → `FindDefinitions` (AST-based, SQL LIKE patterns)
- **Find code by structural pattern** → `FindCode` or `SelectCode` (CSS selectors: `.func#name`, `.class > .func`, `.func:has(.call#execute)`)
- **Understand code structure** → `CodeStructure` (top-level overview with line counts)
- **Multi-source search (defs + calls + docs)** → `SearchProject` (one pattern, every place it appears)
- **BM25 full-text search** → `SearchCode` (defs+comments+strings) / `SearchDocs` (markdown) / `SearchContent` (all indexed content)
- **Browse documentation** → `MDOverview` (outline) → `MDSection` (read by section id)
- **Compare git revisions** → `GitDiffSummary` (file-level) → `GitDiffFile` (line-level)
- **Read file at a git revision** → `GitShow`
- **Change review prep** → `ReviewChanges` (changed files + functions by complexity)
- **Browse Claude sessions** → `ChatSessions` / `ChatSearch` / `ChatToolUsage` / `ChatDetail`
- **Direct SQL over the index** → `query` (for macros: `complexity_hotspots`, `module_dependencies`, `structural_diff`, `changed_function_summary`, `doc_outline`)

## Tool reference

### Code analysis
| Tool | Use for |
|---|---|
| `FindDefinitions(file_pattern, name_pattern)` | Definitions by name pattern (SQL LIKE `%`). AST-based, not grep. |
| `FindCode(file_pattern, selector, language?)` | Search code by CSS selector. Composes `:has`, `:not`, combinators. |
| `SelectCode(source, selector)` | View matching code: markdown with file:range headings + source blocks. |
| `ViewCode(file_pattern, selector, context?)` | View matched source with optional context lines around each match. |
| `CodeStructure(file_pattern)` | Top-level structural overview — definitions with line counts. |
| `ExploreProject(root?, code_pattern?, doc_pattern?, top_n?, recent_n?)` | First-contact briefing in one call. |
| `InvestigateSymbol(name, file_pattern?)` | Deep dive: definitions + callers + call sites. |

### Search (BM25 / FTS)
| Tool | Use for |
|---|---|
| `SearchProject(pattern, file_pattern?, doc_pattern?, top_n?)` | Multi-source: definitions + call sites + docs in one call. |
| `SearchCode(query, kind?)` | Code (definitions, comments, string literals). `kind=definition|comment|string`. |
| `SearchDocs(query)` | Markdown documentation sections only. |
| `SearchContent(query, kind?, extractor?)` | All indexed content (docs + code). |
| `FtsStats()` | FTS index health — counts per extractor/kind. |

### Git analysis
| Tool | Use for |
|---|---|
| `GitDiffSummary(from_rev, to_rev, path?)` | File-level change summary between two revisions. |
| `GitDiffFile(file, from_rev, to_rev)` | Line-level unified diff of a single file. |
| `GitShow(file, rev)` | File content at a specific git revision. |
| `ReviewChanges(from_rev?, to_rev?, file_pattern?, top_n?)` | Changed files + functions ranked by complexity. |

### Documentation
| Tool | Use for |
|---|---|
| `MDOverview(pattern?, search?, max_level?)` | Markdown section outlines with optional keyword filter. |
| `MDSection(file_path, section_id)` | Read a section by ID from a markdown file. |

### Conversation history
| Tool | Use for |
|---|---|
| `ChatSessions(project?, days?, limit?)` | Browse sessions (metadata, duration, tool usage, tokens). |
| `ChatSearch(query, role?, project?, days?, limit?)` | Full-text search across messages (user + assistant). |
| `ChatToolUsage(project?, session_id?, days?, limit?)` | Tool usage frequency patterns across sessions. |
| `ChatDetail(session_id)` | Deep view of a single session: metadata, costs, per-tool breakdown. |

### Database + SQL
| Tool | Use for |
|---|---|
| `query(sql, format?)` | Read-only SQL over the index. Use for macros (see below). |
| `list_tables(schema?, database?, include_views?)` | Available tables + schemas + row counts. |
| `describe(table?, query?)` | Schema info for a table or query. |
| `ReadLines(file_path, lines?, ctx?, match?, commit?)` | Read line range with optional context/filter; supports git revisions. |
| `Help(section?)` | Skill guide — call with no args for outline, with section id for detail. |

## Advanced queries

Fledgling also exposes a `query` built-in tool for direct SQL. Useful macros:

```sql
-- Find complexity hotspots
SELECT * FROM complexity_hotspots('src/**/*.py', 10);

-- Module dependency analysis
SELECT * FROM module_dependencies('src/**/*.py');

-- Structural diff (function-level changes)
SELECT * FROM structural_diff('HEAD~1', 'HEAD', 'src/**/*.py');

-- Changed function summary
SELECT * FROM changed_function_summary('HEAD~3', 'HEAD');
```

## Requirements

- DuckDB with extensions: `duckdb_mcp`, `duck_tails`, `markdown`, `read_lines`, `sitting_duck`
- Project must be initialized: `curl -sL https://teaguesterling.github.io/fledgling/install.sql | duckdb`
