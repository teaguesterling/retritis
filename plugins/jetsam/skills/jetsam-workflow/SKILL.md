---
name: jetsam-workflow
description: Use this skill for ALL git and GitHub workflow operations. Triggers on commit/save, push/sync, ship, release/tag, open or merge PR, check CI, manage issues, start/switch/finish a branch, or anything phrased like "ship it", "bump and tag", "merge when green", "release v...". Route through jetsam workflow verbs (save / sync / ship / release / start / switch / finish / tidy / checks) — NOT raw `git`/`gh` via Bash and NOT the low-level `mcp__jetsam__git` passthrough. Workflow verbs return plans you confirm() before they execute, catching mistakes before history is written. Use the `git` passthrough only when no workflow verb fits.
version: 1.0.1
---

# Jetsam Git Workflow

JetSam is a git workflow accelerator available as an MCP server. Use JetSam
tools instead of running git or gh commands through Bash.

## How it works

- **Workflow operations** (save, sync, ship, etc.) return execution plans.
  Review the plan, then call `confirm()` to execute.
- **Plan lifecycle**: a returned plan can be re-displayed with
  `mcp__jetsam__show_plan(id=...)`, adjusted with
  `mcp__jetsam__modify_plan(id=..., ...)` before confirming, or discarded
  with `mcp__jetsam__cancel(id=...)` to abort it without touching history.
- **Query operations** (status, log, diff, etc.) return results directly.
- **All errors** return `{error, message, recoverable}` dicts.

## Targeting a non-cwd repo: use `cwd=`, NOT `git -C`

Every workflow verb (`status`, `save`, `sync`, `ship`, `start`, `finish`,
`tidy`, `release`, `log`, `diff`, `switch`, `pr_*`, `issues`, `issue_close`,
`checks`) accepts `cwd: str | None = None` (as of jetsam `33d5869`,
2026-06-06). Set it to operate on another repo; omit it to use the process
cwd.

**To add/commit/push in a different repo, pass `cwd=` to the workflow verb —
do NOT fall through to `mcp__jetsam__git(args=["-C", path, ...])`.** The
passthrough skips the plan/confirm safety and the structured state the
workflow verbs return; reaching for `git -C` is the single most common way
this skill gets bypassed.

```
# Cross-repo work — the right way:
mcp__jetsam__status(cwd="/home/teague/Projects/other")
mcp__jetsam__save(message="fix", cwd="/home/teague/Projects/other")   # not: git -C other add && commit
mcp__jetsam__sync(cwd="/home/teague/Projects/other")                  # not: git -C other push
mcp__jetsam__ship(message="fix", cwd="/home/teague/Projects/other")   # not: git -C other add+commit+push
```

The `mcp__jetsam__git` passthrough (which supports `-C <path>`) is the
fallback ONLY for operations no workflow verb covers: LFS hook bypass with
`--no-verify`, admin-bypass merges, force-with-lease pushes, cross-fork
pushes, heredoc commit bodies. If a verb covers it, use the verb with `cwd=`.

**Stale-jetsam symptom:** if `cwd=` is silently dropped, the verb returns a
state whose `repo_root` doesn't match the path you passed — upgrade jetsam
rather than reverting to `git -C`.

## Routing table

Do NOT run git or gh commands through Bash. Use these JetSam MCP tools instead:

| Instead of... | Use JetSam |
|---|---|
| `git status` | `mcp__jetsam__status` |
| `git add && git commit` | `mcp__jetsam__save` |
| `git push` / fetch+merge+push | `mcp__jetsam__sync` |
| `git add && commit && push && gh pr create` | `mcp__jetsam__ship` |
| `git checkout -b` to work on issue/feature | `mcp__jetsam__start` |
| `git checkout` / `git switch` (existing branch) | `mcp__jetsam__switch` |
| `git log` | `mcp__jetsam__log` |
| `git diff` | `mcp__jetsam__diff` |
| `gh pr merge` + branch cleanup | `mcp__jetsam__finish` |
| Branch pruning / cleanup | `mcp__jetsam__tidy` |
| `gh pr view` | `mcp__jetsam__pr_view` |
| `gh pr list` | `mcp__jetsam__pr_list` |
| `gh pr checks` / `gh run view` | `mcp__jetsam__checks` |
| `gh pr comment` | `mcp__jetsam__pr_comment` |
| `gh pr review` | `mcp__jetsam__pr_review` |
| `gh api .../comments` (read PR comments) | `mcp__jetsam__pr_comments` |
| `gh issue list` | `mcp__jetsam__issues` |
| `gh issue close` | `mcp__jetsam__issue_close` |
| `gh release create` | `mcp__jetsam__release` |
| Other git commands | `mcp__jetsam__git` (passthrough) |

## Workflow patterns

### Save and ship (most common)
1. `mcp__jetsam__save(message="fix bug")` → returns plan
2. `mcp__jetsam__confirm(id=plan_id)` → executes
3. `mcp__jetsam__ship(message="fix bug")` → stage+commit+push+PR in one plan

### Check status before acting
1. `mcp__jetsam__status()` → branch, dirty state, ahead/behind, PR info
2. Decide next action based on state

### Sync before push
1. `mcp__jetsam__sync()` → fetch+rebase/merge+push plan
2. `mcp__jetsam__confirm(id=plan_id)`

### Start work on an issue
1. `mcp__jetsam__start(target="42")` → creates branch from issue number
2. `mcp__jetsam__confirm(id=plan_id)`
