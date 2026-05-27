# 7. jetsam — Git, as a Workflow

jetsam is a git *workflow* accelerator: it wraps the common branch/commit/sync/PR dance in
named, intention-level operations, and — crucially — **mutating operations return a plan
you must confirm** before anything happens. It is the "persist" step of the loop.

## Workflow tools vs the escape hatch

- **Read tools** (run freely): `status`, `log`, `diff`, `show_plan`, `pr_list`, `pr_view`,
  `pr_comments`, `checks`, `issues`.
- **Mutating tools** (return a plan → `confirm()`): `save` (stage+commit),
  `sync` (pull/rebase/push), `start` (begin a branch/task), `finish`, `ship` (open/update a
  PR), `release`, `switch`, `tidy`, `modify_plan`, `issue_close`, `pr_comment`,
  `pr_review`, `cancel`.
- **`git`** — the escape hatch for any operation the workflow tools don't cover. Reach for
  it last, not first.

Errors come back as `{error, message, recoverable}` — check for the `error` key.

## The confirm model

```
jetsam.save(...)        # returns a PLAN: "will stage X, commit with message Y"
jetsam.confirm(...)     # executes the plan
```

> **Why plan-then-confirm.** Git mistakes are annoying to undo and easy to make
> autonomously (committing the wrong files, rebasing the wrong branch). Returning a plan
> turns "I ran a mutation" into "I proposed a mutation, then approved it" — a checkpoint
> that catches the wrong-files/wrong-branch class of error before it lands.

> **Agent Recipe — commit your work.**
> `jetsam.status` (see what's staged/changed) → `jetsam.save` (get the plan) → read the
> plan → `jetsam.confirm`. For a PR: `jetsam.ship` → confirm; then `jetsam.pr_view`.

## Where it fits

jetsam is the persist edge of the observe→act→verify→**persist** loop. You observed with
squackit, acted by editing, verified with blq; jetsam turns the result into commits and
PRs without you hand-assembling git commands — and without the foot-guns of doing so
autonomously.
