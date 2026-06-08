# Plan: uniform in-memory `config()` endpoint across jetsam, squackit, blq

## Context

In this session (2026-06-07) we shipped Part A (jetsam `cwd=` + squackit `path=`)
and Part B (test-failure-investigator orchestration skill). Discussion that
followed: "do we need `cwd=` on every command, or is there a session-level
'active repo'?" Decision was to stay with explicit `cwd=` per call for safety
(option 1 in that thread), and to design a small uniform config endpoint as a
follow-up that *could* hold an `active_root` alongside other runtime knobs.

lackpy already has the shape (`config()` reads/updates provider/model/kits).
This plan extends that pattern to jetsam, squackit, blq so the suite has a
uniform discovery surface for runtime tuning.

## Design decisions (already made)

- **In-memory only.** No disk persistence. Server restart resets to defaults.
- **Env-var seeding at launch is allowed.** Setting `JETSAM_ACTIVE_ROOT` in
  `.mcp.json` env block seeds the in-memory config at startup. The server
  still holds it in RAM — env vars are the persistence mechanism, not the
  server's own state.
- **Same shape on each server**, not a single shared service. Each MCP server
  owns its own `config()`. Reduces coupling; each server can evolve its key
  set independently.

## API shape

Every server exposes one tool:

```
config()                          # → returns current config as a flat dict
config(set={"key": "value"})      # → merge into current, return new state
config(reset=true)                # → reset to compile-time + env-var-seeded defaults
```

Each call returns the *full current config* so the agent can verify what's
set without a second read. Unknown keys in `set=` raise (don't silently
accept — too easy to typo and never notice).

## Common keys (all three servers)

| key            | type    | default     | purpose                                  |
|----------------|---------|-------------|------------------------------------------|
| `active_root`  | path    | process cwd | fallback when `cwd=` param is omitted    |
| `log_level`    | str     | "info"      | debug / info / warn / error              |

## Per-server keys (starter list — refine in spec phase)

### jetsam
- `default_sync_strategy` — "rebase" | "merge" (today: rebase)
- `default_base_branch` — usually "main"
- `signing_required` — bool; fail early if GPG isn't configured
- `auto_confirm_safe_verbs` — allowlist (default empty; e.g. `["status", "log"]`
  would already be auto since they're query-only, so this is really for *plans*
  the user wants to bypass confirm on)

### squackit
- `code_pattern_default` — replaces `defaults.code_pattern` for callers who
  don't pass `file_pattern=`
- `max_results_default` — tune token-aware truncation
- `fts_cache_size` — LRU size for per-root FTS (today: implicit)
- `complexity_max_results_default`

### blq
- `capture_buffer_size` — inline output cap
- `default_retention_days`
- `default_lines_window` — default for `run(lines=...)` when omitted
- `auto_register_from_history` — promote frequently-exec'd commands to
  registered

## Open questions (resolve in spec phase)

1. **Reset semantics.** Does `reset=true` go to *compile-time defaults* or
   to *env-var-seeded values*? Argue: env-var seeded — that's what the user
   configured via `.mcp.json`, the "fresh start" they want.
2. **Schema validation.** Pydantic model per server? Or a flat dict with a
   docstring? Pydantic gives free type checking + a discoverable schema;
   flat dict is lighter.
3. **Atomic batched-set.** `config(set={a: 1, b: 2})` — if `b` fails
   validation, does `a` get applied? Recommend: validate-all-then-apply,
   atomic.
4. **Cross-server keys.** If three servers all expose `active_root`, does an
   agent need to set it three times? Yes (each server is independent). A
   future "retritis config" CLI could broadcast, but that's out of scope.
5. **Discoverability.** Add `## Configuration` section to each plugin's
   SKILL.md? Or one central `docs/CONFIG.md` in retritis? Probably both:
   per-plugin section for the tool's keys, central doc for the cross-suite
   convention.

## Implementation order

1. **jetsam first** — smallest surface, currently stateless, easiest to
   verify the pattern. Ship `config()` + `active_root` + `default_sync_strategy`
   as MVP. ~half day including tests + SKILL.md update.
2. **squackit** — has existing `ProjectDefaults` + per-root FTS caching that
   need to integrate cleanly with the new endpoint. Don't break existing
   `root=` / `path=` params; `config(set={"active_root": X})` should make
   them optional, not change their meaning when passed.
3. **blq** — most existing state (DB-backed runs + registered commands).
   Careful separation: persistent state stays in the DB; runtime knobs go
   in `config()`. Don't conflate.

## SKILL.md updates (after implementation)

- Each plugin SKILL.md gets a `## Configuration` section showing `config()`
  invocation + the tool's key inventory.
- The test-failure-investigator skill gets a "if you're investigating in a
  non-cwd repo, set `active_root` once via `config(set=...)` instead of
  threading `cwd=` through every call" note.

## Out of scope (for this plan)

- Cross-server broadcast (one call updates all three) — could be a thin CLI
  later, not the MCP layer's job.
- Disk persistence — explicit rejection.
- A retritis-wide MCP "control plane" server — overkill for runtime knobs;
  per-server `config()` keeps coupling low.

## Status

**Jetsam prototype shipped on `feat/config-endpoint` (2026-06-07, commit `cdd243a`).**
Pushed to origin; branch ready for PR / merge.

What landed:
- `src/jetsam/config/runtime.py` (new) — `JetsamRuntimeConfig` dataclass +
  `get_runtime()` / `update_runtime()` / `reset_runtime()` singleton API +
  env-var seeding via `JetsamRuntimeConfig.from_env()`.
- `src/jetsam/mcp/tools.py` — new `config()` MCP tool: read / set / reset.
- `src/jetsam/core/state.py` — `build_state(cwd=None)` falls back to
  `runtime.active_root` when cwd is omitted. Explicit cwd= still wins.
- `tests/test_runtime_config.py` (new, 19 tests, all green; full suite 395 green).

Shape validated for resolutions in the original plan:
1. **Reset semantics**: chose env-seeded values (not compile-time defaults).
2. **Schema validation**: stuck with a flat dict + dataclass + per-key
   `_validate_one` helper. No pydantic; instance-creation cost minimal.
3. **Atomic batched-set**: yes — validate all keys, then apply; unknown keys
   raise before any change.
4. **Discoverability**: jetsam SKILL.md updated; retritis CONFIG.md TBD.
5. **Cross-server keys**: kept as a documented convention (active_root,
   log_level present in jetsam; same names will be used in squackit/blq).

**Squackit prototype shipped on `feat/config-endpoint` (2026-06-07, PR #6,
merged at `6ca27e4`).** Pushed; pending next release.

What landed:
- `squackit/runtime.py` (new) — `SquackitRuntimeConfig` dataclass + same
  `get_runtime()` / `update_runtime()` / `reset_runtime()` API as jetsam, plus
  `resolve_scope_path()` helper (precedence: explicit → active_root → cwd).
- `squackit/workflows.py` — new `config()` MCP tool registered via
  `_add_workflow_tool`; `investigate()` now calls `resolve_scope_path()`
  instead of `path or os.getcwd()`.
- `tests/test_runtime_config.py` (new, 21 tests, all green; full suite 303 green).

Cross-server convention validated: same shape works on both servers
(jetsam + squackit). Common keys (`active_root`, `log_level`) carry the
same semantics; per-server keys (jetsam: `default_sync_strategy`,
`signing_required`; squackit: `max_results_default`, `fts_cache_size`)
fit cleanly without coupling.

Still to do (deferred):

- **blq**: source TBD (check blq's MCP layer structure), tests. Careful
  separation: persistent state stays in the DB; runtime knobs go in
  `config()`.
- **retritis**: `docs/CONFIG.md` (central convention doc) — write after the
  shape's been validated in production for a couple of sessions.
- **Per-server semantic enrichment**: jetsam should consume
  `default_sync_strategy` / `signing_required` (today they're knobs no
  workflow verb actually reads); squackit should consume
  `max_results_default` (today it's a stored knob, not applied).
