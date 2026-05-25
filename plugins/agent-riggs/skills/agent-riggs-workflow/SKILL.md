---
name: agent-riggs-workflow
description: Cross-session memory and trust analysis for agents. Use to ingest prior-session data, get a briefing, check trust scores, and surface recurring patterns worth promoting (ratchets). CLI, not an MCP server.
---
# agent-riggs — cross-session memory & analysis

No MCP server — it's a CLI over a `.riggs/` store. Initialize once: `agent-riggs init`.

- `agent-riggs brief` — full session briefing (what happened, patterns, risks)
- `agent-riggs ingest` — pull session data from sibling tools (kibitzer, blq, jetsam, fledgling)
- `agent-riggs status` — trust scores, mode, ratchet summary
- `agent-riggs trust` — trust-score commands
- `agent-riggs ratchet` — candidate patterns worth promoting to templates
- `agent-riggs metrics` — ratchet metrics dashboard
