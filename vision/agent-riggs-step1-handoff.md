# Handoff: agent-riggs Step 1 — the ratchet's first closed loop

A pick-up prompt for a fresh session to continue the agent-riggs build. Step 0
is done; this is Step 1 of the duck-parser plan in agent-riggs
`docs/superpowers/specs/2026-06-20-system4-synthesis.md`.

## What you're picking up

The Rigged / retritis suite (`teaguesterling/*`): Claude Code plugins steering
agents toward structured tools over raw shell. Tools you'll touch:

- **agent-riggs** (`~/Projects/agent-riggs`) — cross-session audit/intelligence,
  framed as Beer VSM **System 3\***. Already substantially built: plugin
  architecture (trust/ingest/ratchet/metrics/briefing/sandbox), DuckDB store,
  trust scoring, the ratchet, ingest sources for kibitzer/blq/jetsam/fledgling.
  **Deterministic by design** (Principle #3).
- **kibitzer** — within-session tool-call observer + nudges (grep→squackit, etc.).
  Now runs an **A/B experiment**: each eligible bypass is randomly NUDGE vs
  silent CONTROL, with "heed" (did the agent use the suggested tool within the
  window) logged to `~/.kibitzer/nudge_trials.jsonl` =
  `{plugin, arm, heed, turns_to_heed, session}`.
- **fledgling** — `sql/conversations.sql` parses Claude transcripts into macros:
  `tool_calls()`, `bash_commands()` (with `category` + a **`replaceable_by`**
  column), `session_summary()`.
- **squackit / blq / jetsam / lackpy** — the structured tools agents should prefer.

**Read first (in order):**
1. `~/Projects/agent-riggs/docs/superpowers/specs/2026-06-20-system4-synthesis.md`
   — reconciled architecture (System 3\* core ⊕ System 4) + staged plan.
   **Step 0 done; you are doing Step 1.**
2. `~/Projects/agent-riggs/docs/the-ratchet.md` + `docs/architecture.md`
   — existing deterministic design + Principle #3.
3. `~/Projects/retritis/scripts/bypass.sql` — Step 0 output (bypass as SQL).

## Done already (Step 0)
- Transcripts are a queryable table — fledgling's `conversations.sql` already
  provides it; no parser to build.
- `retritis/scripts/bypass.sql` reproduces the per-plugin preference picture as
  SQL (jetsam strongest preference, squackit weakest).
- Key finding: `bash_commands().replaceable_by` is essentially the ratchet's
  tool-promotion signal, already maintained in fledgling.

## Your task: Step 1 — wire telemetry into the ratchet, deterministically
1. **Ingest source** (`src/agent_riggs/ingest/sources/`, follow `base.py` +
   `kibitzer.py`): read `~/.kibitzer/nudge_trials.jsonl` into a new store table
   (owned via a plugin's `schema_ddl()`).
2. **Candidate view** (`src/agent_riggs/ratchet/candidates.py`): a tool-promotion
   candidate combining **frequency** (fledgling `replaceable_by` / bypass.sql)
   **with A/B heed evidence**. Must NOT graduate on frequency alone.
3. **Promotion wiring** — action exists (`ratchet promote` writes
   `.kibitzer/config.toml` `[plugins.X] mode`); register the new candidate type.
   Still human-gated.

## The point (honor this)
The existing ratchet promotes on **frequency** ("grep used 89× → graduate"). This
session proved (kibitzer A/B + `nudge_lift`) that **frequency ≠ behavior-change.**
The candidate view must require **measured heed/lift**, not counts. That closes
the correlation/causation gap — the whole advance. No frequency-only candidate.

## Constraints — do NOT violate
- **Deterministic. No LLM in the decision loop** (Principle #3 refined: LLM may
  write *data* / *propose*; only SQL + human *decide*). Step 1 is pure SQL +
  plumbing — no LLM, no System-4 layer yet (Steps 2–4, earned later).
- **Reads everything, writes nothing** to other tools except via human-gated
  `ratchet promote`. The view *surfaces* candidates; never auto-promotes.
- DuckDB-native; plugin protocol (`schema_ddl`/`cli_commands`/`mcp_tools`);
  graceful degradation (no nudge_trials file → no candidates, not a crash).
- **agent-riggs commits are UNSIGNED.** (retritis commits are signed — run
  `gpg-unlock` if signing fails with "Bad passphrase".)

## Verify
- agent-riggs tests pass.
- `agent-riggs ratchet candidates` shows the new type over real data.
- Show one candidate with high frequency but LOW heed, and confirm it is NOT
  surfaced for promotion. That proves the gap is closed.

## Don't
- Don't build the System-4 / LLM / experiment-generator layer (Steps 2–4).
- Don't overturn the deterministic ratchet or auto-apply promotions.
- Don't rebuild the transcript parser (it's fledgling's `conversations.sql`).

## When done
Report the new source + table + candidate view + type, test results, and the
frequency-high/heed-low example. Then tee up **Step 2**: generalize the kibitzer
A/B into an experiment the ratchet can *request* (System-4 evidence generation).
