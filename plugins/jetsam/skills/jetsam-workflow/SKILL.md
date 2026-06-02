---
name: jetsam-workflow
description: Use this skill for ALL git and GitHub workflow operations. Triggers on commit/save, push/sync, ship, release/tag, open or merge PR, check CI, manage issues, start/switch/finish a branch, or anything phrased like "ship it", "bump and tag", "merge when green", "release v...". Route through jetsam workflow verbs (save / sync / ship / release / start / switch / finish / tidy / checks) — NOT raw `git`/`gh` via Bash and NOT the low-level `mcp__jetsam__git` passthrough. Workflow verbs return plans you confirm() before they execute, catching mistakes before history is written. Use the `git` passthrough only when no workflow verb fits.
version: 1.0.0
---

# Jetsam Git Workflow

JetSam is a git workflow accelerator available as an MCP server. Use JetSam
tools instead of running git or gh commands through Bash.

## How it works

- **Workflow operations** (save, sync, ship, etc.) return execution plans.
  Review the plan, then call `confirm()` to execute.
- **Query operations** (status, log, diff, etc.) return results directly.
- **All errors** return `{error, message, recoverable}` dicts.

## Important: workflow tools target the current working directory

Both workflow verbs (`status`, `save`, `sync`, `ship`, etc.) and query tools
(`log`, `diff`) operate on the **current working directory's** git repo.
They do NOT accept a `-C` / `cwd` / `path` argument — passing one is silently
ignored and you get results for the wrong repo.

**When you need cross-repo operations** (typing inside repo A but want to act
on repo B), use the `mcp__jetsam__git` passthrough with `-C <path>` instead:

```
# WRONG — silently runs against cwd, not /home/teague/Projects/other
mcp__jetsam__status(args=["-C", "/home/teague/Projects/other"])

# RIGHT — passthrough explicitly targets the path
mcp__jetsam__git(args=["-C", "/home/teague/Projects/other", "log", "--oneline", "-5"])
```

This is one of the legitimate uses of the passthrough — workflow verbs
intentionally bind to cwd to keep their plan-state coherent.

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
