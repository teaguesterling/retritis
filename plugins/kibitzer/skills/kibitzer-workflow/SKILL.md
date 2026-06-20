---
name: kibitzer-workflow
description: Kibitzer observes your tool calls and suggests structured alternatives (raw grep→squackit, build/test→blq) — advisory, never blocking in the default mode. Use its MCP tools to drive it — ChangeToolMode to set a write-scope guardrail, GetFeedback to see what it's noticing, GetDocContext for tool/error help — otherwise just let it watch. Triggers on "switch kibitzer mode", "scope my writes to src", "what is kibitzer suggesting", "check kibitzer feedback".
version: 1.0.1
---

## What kibitzer does

Kibitzer watches your tool calls (via PreToolUse/PostToolUse hooks) and, when
you reach for a raw shell command that a structured tool covers, surfaces an
**advisory** suggestion — never a block, in the default mode:

- `grep -rn "pattern"` → "squackit suggests: `search` / `find_code_ranked`"
- `cargo build` / `pytest` → "blq suggests: `blq run`/`blq exec` — captures + indexes output"

Nudges are advisory context, not enforcement — ignore them when they don't
apply. Each plugin nudges **at most once per session** (no nagging).

> Kibitzer runs an A/B experiment: it randomly *withholds* some nudges to
> measure whether nudging changes behavior. A missing nudge may just be the
> control arm — that's intentional.

## MCP tools

- **`ChangeToolMode(mode)`** — switch the write-scope mode. `free` (default)
  writes anywhere and never denies. The restrictive modes are **opt-in
  guardrails**: `implement` (writes only `src/`+`lib/`), `test` (`tests/`),
  `docs` (`docs/`+READMEs), `explore`/`review` (read-only). Reach for one
  deliberately — e.g. `ChangeToolMode("implement")` to fence yourself to source
  during a refactor — then `ChangeToolMode("free")` to release it.
- **`GetFeedback()`** — current status: mode, coaching suggestions, and the
  patterns kibitzer has intercepted this session. Call it to see what it's noticing.
- **`GetDocContext(query)`** — search registered documentation when you're stuck
  on a tool or an error; returns relevant sections (or nothing).

## Modes at a glance

| Mode | Writable | Use when |
|---|---|---|
| `free` (default) | everything | normal work — no guardrails, never blocks |
| `implement` | `src/`, `lib/` | fencing yourself to source during a refactor |
| `test` | `tests/`, `spec/` | writing tests only |
| `docs` | `docs/`, `*.md` | docs-only changes |
| `explore` / `review` | (read-only) | mapping or reviewing before changing |

## How to use

Mostly, let it watch — the nudges come to you. Reach for the MCP tools when you
want to *drive* it: set a restrictive mode to guardrail a risky edit session,
`GetFeedback()` to see intercepted patterns, or `GetDocContext()` for help. The
restrictive modes can **deny** writes outside their scope, so switch back to
`free` when you're done.
