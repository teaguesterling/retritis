# 9. lackpy — Intent to Program with Local Models

lackpy turns a natural-language *intent* into a small, restricted, runnable program. It is
"Python that lacks most of Python": a deliberately narrow language a model can target
safely, generated (often by a **local** model on GPU) and executed under tight controls.

## The pipeline

```
intent (NL) ─► generate (local model) ─► validate (restricted grammar) ─► run (sandboxed)
```

- **generate** — produce a program from intent. The model is configurable
  (`lackpy.provider_list`, `config`); on this suite's GPU host it is a local ollama model
  (e.g. `qwen3:14b`), so generation is private and cheap.
- **validate** — the program must parse within lackpy's restricted grammar
  (`ALLOWED_NODES`/`FORBIDDEN_NODES`, `ALLOWED_BUILTINS`/`FORBIDDEN_NAMES`). This is a
  language-level guarantee, not a prompt request.
- **run_program / delegate** — execute under a `RestrictedRunner`, with a **kit** of
  allowed tools and a sandbox (Chapter 12).

CLI: `lackpy -c "<intent>" [--generate|--validate|--create]`; `lackpyctl` manages
workspaces, kits, toolboxes, templates, and the MCP server. `language_spec` documents the
allowed language — read it before assuming a Python feature exists.

## Kits and toolboxes

A **kit** is the resolved set of tools/callables a generated program may use; a **toolbox**
is where those come from. `kit_list`/`kit_info`/`kit_create`, `toolbox_list`. The kit is
the upper bound on capability: policy can *restrict* the kit but never grant beyond it.

## The policy chain

lackpy resolves what a program may do through a chain of **policy sources**, highest
priority first. Three matter here:

- **kit** — ground truth for available tools.
- **kibitzer** — coaching/hints from the session.
- **umwelt** — the world-model policy: it can hide/deny tools and attach constraints
  (max-level, allow/deny path patterns), read from the same compiled `policy.db` kibitzer
  uses (Chapter 11). This is the *second* enforcer of "one policy, two enforcers."

> **Why mode matters here.** The umwelt source resolves tool policy for the *active mode*.
> Originally lackpy was mode-blind — it resolved with no context, so a rule like
> "deny `Bash` in review mode" leaked into *every* mode and over-restricted. The fix added
> `mode` to lackpy's `PolicyContext` and threaded it into the resolve call, so a generated
> program is restricted for the mode the agent is actually in. If you wire a new policy
> source, thread the mode.

## When to reach for lackpy

When a task is better expressed as "generate a small program to do X over these tools" than
as a sequence of your own tool calls — data munging, a structured transform, a one-off
analysis — and you want it generated locally and run safely. For ordinary code
understanding, stay with squackit; lackpy is for *generating and running* constrained code.
