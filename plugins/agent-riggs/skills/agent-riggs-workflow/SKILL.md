---
name: agent-riggs-workflow
description: Cross-session memory and trust analysis for agents. Triggers on "audit tool usage" / "which tools are being used" / "brief me on this project" / "start-of-session context" / "what happened in prior sessions" / "am I repeating past mistakes" / "what patterns recur" / "cross-session" / "trust scores" / "ratchet candidates" / "what should be promoted to a template". Use to ingest prior-session data, get a briefing, check trust scores, and surface recurring patterns worth promoting (ratchets). CLI, not an MCP server (a SessionStart hook auto-ingests + briefs in projects that ran `agent-riggs init`; these commands drive it directly).
---
# agent-riggs — cross-session memory & analysis

No MCP server — it's a CLI over a `.riggs/` store. Initialize once: `agent-riggs init`.

- `agent-riggs brief` — full session briefing (what happened, patterns, risks)
- `agent-riggs ingest` — pull session data from sibling tools (kibitzer, blq, jetsam, fledgling)
- `agent-riggs status` — trust scores, mode, ratchet summary
- `agent-riggs trust` — trust-score commands
- `agent-riggs ratchet` — candidate patterns worth promoting to templates
- `agent-riggs metrics` — ratchet metrics dashboard
