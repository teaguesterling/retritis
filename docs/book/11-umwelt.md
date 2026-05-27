# 11. umwelt — Policy as a Cascade

umwelt lets you author policy the way you author a stylesheet: a **world** of entities plus
a **cascade** of rules with specificity, compiled into a DuckDB `policy.db` that the
enforcers (kibitzer, lackpy) read. One authored source; two consumers; no divergence.

## World + stylesheet

- **world** (YAML): the entities policy resolves over — `{type, id, classes}`, e.g. tools
  (`Read`, `Edit`, `Bash` with class `dangerous`) and modes (`implement`, `review`).
- **stylesheet** (`.umw`): CSS-like rules over those entities:

```css
tool                 { allow: true; max-level: 8; }
tool.dangerous       { max-level: 5; }
mode#review tool     { allow: false; }          /* in review, deny tools... */
mode#review tool[name="Read"] { allow: true; }  /* ...except Read */
mode#implement { writable: "src/,tests/"; strategy: "tdd"; }
```

Compile and query:

```python
from umwelt.policy import PolicyEngine
eng = PolicyEngine.from_files(world=world, stylesheet=style)
eng.save("policy.db")                                   # the compiled contract
eng = PolicyEngine.from_db("policy.db")                 # consumers reopen it
eng.resolve(type="tool", id="Bash", property="allow", context={"mode": "review"})
```

## The cascade

Resolution follows CSS-like **specificity**: more specific selectors win, mode-scoped rules
(`mode#review tool`) apply when that mode is active. `resolve` returns one property;
`resolve` with no `property` returns the whole resolved dict; `resolve_all` returns every
entity of a type. Mode is passed as `context={"mode": ...}` (the older `mode=` kwarg is
deprecated).

> **Why a cascade.** Policy is naturally layered: a global default, a class-based
> tightening, a per-entity exception, a mode-scoped override. CSS already solved "layered
> rules with deterministic precedence." Reusing specificity means policy authors reason
> about overrides the way they already do for stylesheets, and the resolution is explainable
> (`trace` shows the competing candidates).

## One policy, two enforcers

The compiled `policy.db` is read by **kibitzer** (governs the agent: `get_mode_policy`,
`get_tool_policy`) and **lackpy** (restricts generated programs: `UmweltPolicySource`). The
invariant — *the same policy yields the same verdict on both surfaces* — is enforced by a
conformance test that resolves every (mode, tool) three ways (the engine itself, the
kibitzer consumer, the lackpy source) and requires zero divergence. That harness is how a
real bug was caught: lackpy read a flat dict the engine never produced, and it crashed on
the first real policy. The conformance is now the tripwire.

> **The producer is the source of truth.** When you test a consumer of a cascade, drive the
> *real* engine to produce the expected verdict; don't hand-roll fixtures of "what the
> policy should say." A fixture encodes your belief; the engine encodes the contract.

## Authoring tips

- Keep the world minimal — only entities you actually scope rules to.
- Prefer mode-scoped overrides to duplicating rules per mode.
- After editing a `.umw`, recompile to `policy.db`; both enforcers pick it up on next load.
