---
name: jetsam-workflow
description: Use this skill for ALL git and GitHub operations. When the user asks to commit, push, create PRs, check CI, manage issues, or any git workflow task, route through jetsam MCP tools instead of running git/gh commands through Bash.
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
