---
name: blq-workflow
description: Use this skill for ALL build, test, and CI operations. When the user asks to run tests, build, check lint, run type checking, or analyze build output, route through blq MCP tools instead of running commands through Bash. Also use when analyzing errors, filtering output, or checking CI status.
version: 1.0.0
---

# blq — Build Log Query

blq captures and queries build/test output. Use blq MCP tools instead of
running build commands through Bash directly.

## Why blq instead of Bash

- Output is captured and indexed — query it later without re-running
- Structured error/warning extraction — no grep needed
- No shell pipes or redirects — use `output()` to filter after the fact
- History of all runs — compare across builds

## Routing table

Do NOT run build/test commands through Bash. Use blq MCP tools instead:

| Instead of... | Use blq |
|---|---|
| `pytest tests/` | `mcp__blq_mcp__run(command="test")` |
| `make build` | `mcp__blq_mcp__run(command="build")` |
| `ruff check src/` | `mcp__blq_mcp__run(command="lint")` |
| `mypy src/` | `mcp__blq_mcp__run(command="typecheck")` |
| Piping output through tail/grep | Run first, then use `mcp__blq_mcp__output(tail=20)` or `output(grep="FAIL")` |
| Ad-hoc shell commands | `mcp__blq_mcp__exec(command="any shell command")` |

## Key tools

### Run registered commands
```
mcp__blq_mcp__commands()           # list available commands
mcp__blq_mcp__run(command="test")  # run a registered command
mcp__blq_mcp__run(command="test", lines="+20-")  # run and get last 20 lines inline
```

### Analyze results
```
mcp__blq_mcp__status()             # current build/test status
mcp__blq_mcp__errors()             # view errors from recent runs
mcp__blq_mcp__output(tail=20)      # last 20 lines of output
mcp__blq_mcp__output(grep="FAIL")  # search output
mcp__blq_mcp__info(ref="latest")   # detailed run info
mcp__blq_mcp__events()             # all events (errors, warnings, info)
```

### Drill into issues
```
mcp__blq_mcp__inspect(ref="latest")  # inspect a specific run
mcp__blq_mcp__history()              # run history
mcp__blq_mcp__diff()                 # compare runs
```

## Important rules

1. **Never use shell pipes** — run the command, then filter with `output()`
2. **Check `commands()` first** — see what's registered before running
3. **Use `run()` not Bash** for registered commands — `run` captures and indexes output
4. **Use `lines` parameter** on `run()` for quick inline output (e.g., `lines="+20-"` for last 20 lines)
