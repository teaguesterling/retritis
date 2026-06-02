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

- **Find function/class definitions** → `FindDefinitions` (AST-based, not text match)
- **Understand code structure** → `CodeStructure` (top-level overview with line counts)
- **Search by code pattern type** → `FindInAST` (calls, imports, loops, etc.)
- **Compare git revisions** → `GitDiffSummary`, `GitDiffFile`
- **Read file at revision** → `GitShow`
- **Browse Claude sessions** → `ChatSessions`, `ChatSearch`

## Tool reference

### Code analysis
| Tool | Use for |
|---|---|
| `FindDefinitions` | Find functions, classes, variables by name pattern (SQL LIKE `%`) |
| `CodeStructure` | Top-level structural overview — definitions with line counts |
| `FindInAST` | Search by category: calls, imports, definitions, loops, conditionals |

### Git analysis
| Tool | Use for |
|---|---|
| `GitDiffSummary` | File-level change summary between two revisions |
| `GitDiffFile` | Line-level unified diff of a single file between revisions |
| `GitShow` | Show file content at a specific git revision |

### Conversation history
| Tool | Use for |
|---|---|
| `ChatSessions` | Browse Claude Code sessions — duration, tool usage, tokens |
| `ChatSearch` | Search conversation content across sessions |
| `ChatToolUsage` | Analyze tool usage patterns across sessions |
| `ChatDetail` | Detailed view of a specific session |

### Utilities
| Tool | Use for |
|---|---|
| `ReadLines` | Read specific line ranges from files |
| `MDSection` | Extract a section from a markdown file by heading |
| `Help` | Show available fledgling commands and usage |

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
