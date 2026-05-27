# 8. kibitzer — Modes, Coaching, and Policy

kibitzer watches your tool calls and shapes how you work: it puts you in a **mode**,
**coaches** with structured suggestions and documentation, and **enforces policy** (which
paths are writable, which tools are allowed) compiled from umwelt. It is the governance
layer of the loop — the part that makes you legible and keeps you on the rails.

## Modes

A mode is a posture: `free`, `implement`, `test`, `docs`, `explore`, `review`. Each defines
what is writable and how kibitzer coaches. For example, `implement` may restrict writes to
`src/`/`tests/`; `review` may be read-only.

- `kibitzer.ChangeToolMode(mode, reason)` — switch deliberately.
- `kibitzer.GetFeedback` — your current mode, coaching suggestions, intercepted patterns.
- `kibitzer.GetDocContext` — search registered documentation for help with a tool/error.

> **Agent Recipe — an edit was refused.** Don't fight it with `bash`. Call
> `kibitzer.GetFeedback` to see the mode and why; if the work legitimately needs writes
> elsewhere, `ChangeToolMode` to the right mode *with a reason*. The mode is a guardrail,
> not an obstacle — switching on purpose is the intended move; tunneling around it is not.

## Hooks

kibitzer runs as `PreToolUse`/`PostToolUse` hooks: before a tool call it can gate or
suggest; after, it can record the outcome and coach. This is how the mode-gate enforces
writable paths and how coaching reacts to a failure. Because it sits on your tool calls,
**it only sees what you do through tools** — another reason to stay tool-first.

## Policy: the consumer side

kibitzer doesn't invent its rules; it *consumes* a compiled policy. `PolicyConsumer.from_db`
reads a `policy.db` produced by umwelt (Chapter 11): mode policy (writable/strategy/
coaching frequency) via `get_mode_policy`, tool policy via `get_tool_policy`. Without a
compiled policy it falls back to a config file — so policy is optional but, when present,
authoritative.

> **Why one policy, two enforcers.** The same compiled `policy.db` is read by kibitzer (to
> govern you in-session) and by lackpy (to restrict generated programs). One authored
> source, two surfaces, no divergence — that invariant is tested by a conformance harness
> in the suite (the "one policy, two enforcers" work). If you author policy, you change
> both enforcers at once; that is the point.

## The learning side

kibitzer is also where cross-session learning *surfaces*. agent-riggs (Chapter 10) promotes
"ratchets" — recorded fixes for recurring failure patterns — and a `RatchetConsumer` lets
kibitzer surface the recorded fix when you hit the same failure fingerprint again. Coaching
that needs documentation context becomes affordable precisely because fledgling's persistent
cache makes the lookup cheap (Chapter 3) — the seams connect.
