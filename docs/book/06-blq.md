# 6. blq — Build-Log Query

blq runs your builds and tests and **captures their output as queryable data** in a local
DuckDB store (`.bird`). It is the "verify" step of the loop. Its whole reason to exist is
the rule:

> **Don't pipe. Run, then query.** `pytest | tail -20` throws the run into your transcript
> and loses it. `blq.run("test")` records the full run; `blq.output(run_id, tail=20)`,
> `blq.errors`, and `blq.query` let you interrogate it afterward — and the *next* session
> can too.

## The model

A **command** is a registered, named way to build/test (`blq.register_command`,
`blq.commands`). You `blq.run("test")`; blq executes it, captures stdout/stderr/exit, and
stores the run. Then you analyze:

- `blq.status` — current/last run state.
- `blq.errors` — extracted errors from a run (the thing you usually want).
- `blq.output(run_id=N, tail=20 | head=… | grep=…)` — filter captured logs **without**
  shell pipes.
- `blq.info(ref)` — detailed run info; refs can be relative (`latest`, `+1`).
- `blq.history`, `blq.events`, `blq.report`, `blq.diff` — across runs.
- `blq.exec` — a captured one-off; `blq.inspect`/`blq.query` — go into the store directly.
- `blq.ci_generate` / `blq.ci_check` — CI scaffolding/validation.

## Why this is better than a terminal

Three reasons, all about *acting on results later*:

1. **Errors are extracted, not eyeballed.** `blq.errors` gives you the failures as records.
2. **Runs persist and compare.** "Did this regress?" is `blq.diff`/`history`, not memory.
3. **It is shared.** The store is the same one the CLI writes to, so a human running
   `blq run build` and you querying the result see the same data.

> **Agent Recipe — the verify step, done right.**
> 1. Once per project: `blq.register_command` your test/build invocations.
> 2. After a change: `blq.run("test")`.
> 3. `blq.status` (pass/fail) → on failure, `blq.errors` (what broke) →
>    `blq.output(run_id, grep="…")` to zoom in. Never `… | tail`.

## A note for this suite

These docs and the suite's own build tooling expect tests/builds to go through blq. If you
find yourself about to run `pytest`/`make`/`npm test` in `bash` and pipe the output, stop:
register it and `blq.run` it instead. The captured run is the artifact, not the scrollback.
