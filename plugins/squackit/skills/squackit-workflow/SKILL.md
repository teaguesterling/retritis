---
name: squackit-workflow
description: Route code intelligence queries through squackit MCP tools instead of grep/find
---

## When to use squackit

Use squackit tools instead of manual searching when you need:

| Instead of... | Use... |
|---------------|--------|
| `grep -r "def function_name"` | `find_names` with pattern matching |
| `grep -r "class ClassName"` | `find_names` with `.cls` selector |
| Multiple greps to trace call chains | `code_structure` for overview, then targeted queries |
| Reading entire files to understand structure | `code_structure` with depth control |

## Available tools

- **find_names** — Find definitions by name pattern and node type
- **code_structure** — Hierarchical code overview with configurable depth
- **find_definitions** — Cross-file symbol resolution
- **find_callers** — Who calls this function/method

## Tips

- squackit caches session state — repeated queries in the same session are fast
- Use glob patterns to scope searches: `find_names "src/**/*.py" ".fn#validate"`
- Token-aware output: results are truncated to fit context windows
