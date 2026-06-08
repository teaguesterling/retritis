---
name: blq-workflow
description: All build, test, and CI operations — capture output, query later. Triggers on "run the tests", "build it", "rebuild", "what errored", "check lint", "run typecheck", "what was the test output", "diff against the previous run", "what's failing in CI". Route through blq MCP tools instead of `pytest`/`make`/`cargo`/`npm` through Bash, because blq captures + indexes output for query without re-running, extracts structured errors (no manual grep), and tracks run history. NO shell pipes — run first, then filter with `output(grep=..., tail=...)`. Use `commands()` to list registered build/test/lint/typecheck targets before running.
version: 1.0.1
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
mcp__blq_mcp__commands()                          # list available commands
mcp__blq_mcp__run(command="test")                 # run a registered command
mcp__blq_mcp__run(command="test", lines="+20-")   # run and return last 20 lines inline
mcp__blq_mcp__exec(command="pytest -k foo")       # ad-hoc command (no pipes/redirects)
mcp__blq_mcp__register_command(name="lint", cmd="ruff check src/")  # register new
mcp__blq_mcp__unregister_command(name="lint")     # remove a registered command
```

### Analyze results
```
mcp__blq_mcp__status()                             # current source status summary
mcp__blq_mcp__events(severity="error")             # filter events — replaces errors()
mcp__blq_mcp__events(severity="error,warning")     # combined filter
mcp__blq_mcp__output(ref="latest", tail=20)        # last 20 lines of a run
mcp__blq_mcp__output(ref="+1", grep="FAIL")        # regex-search captured output
mcp__blq_mcp__info(ref="latest")                   # run metadata + events
```

### Drill in + compare
```
mcp__blq_mcp__inspect(ref="test:1:3")              # event with log/source/git context
mcp__blq_mcp__history(limit=20)                    # recent runs list
mcp__blq_mcp__diff(run1=1, run2=2)                 # error fingerprint diff between runs
mcp__blq_mcp__report(ref="latest")                 # markdown report (good for PRs/CI)
mcp__blq_mcp__query(sql="SELECT * FROM blq_load_events() WHERE ...")  # SQL over events
mcp__blq_mcp__ci_check(baseline="main")            # regression check vs baseline
mcp__blq_mcp__ci_generate(shell="bash")            # emit standalone CI shell scripts from registered commands
```

### Housekeeping
```
mcp__blq_mcp__sandbox_info()                       # sandbox spec + world-coupling grade per command
mcp__blq_mcp__clean(mode="prune", days=30, confirm=True)  # cleanup: data/prune/schema/full (confirm=True required)
```

## Session config — `config()`

Available in blq 1.0.1+ (PR #44 merged 2026-06-07; pending release).
In-memory only — wiped on server restart. Persistent state (run history,
retention, registered commands) stays in the DB.

```
mcp__blq_mcp__config()                                    # read current
mcp__blq_mcp__config(set={"active_root": "/path/to/repo"}) # update
mcp__blq_mcp__config(reset=true)                          # revert to env-seed
```

**The `active_root` key is the cross-repo ergonomics shortcut.** When set,
`_get_storage()` looks for `.bird/` at that path before falling through
to the cwd-walk. Lets you target a different workspace's logs in a
multi-repo session.

Common keys (shared with jetsam/squackit):
- `active_root` — fallback for locating `.bird/` workspace
- `log_level` — debug | info | warn | error

Blq-specific:
- `default_lines_window` — default for `run(lines=...)` when omitted
- `default_history_limit` — default for `history(limit=...)`

Env-var seeding at MCP server launch (via `.mcp.json` env block):
`BLQ_ACTIVE_ROOT`, `BLQ_LOG_LEVEL`, `BLQ_DEFAULT_LINES_WINDOW`,
`BLQ_DEFAULT_HISTORY_LIMIT`. Read once at launch; `config(reset=true)`
reverts to these values.

## Important rules

1. **Never use shell pipes** — run the command, then filter with `output()`
2. **Check `commands()` first** — see what's registered before running
3. **Use `run()` not Bash** for registered commands — `run` captures and indexes output
4. **Use `lines` parameter** on `run()` for quick inline output (e.g., `lines="+20-"` for last 20 lines)
