#!/usr/bin/env bash
# agent-riggs SessionStart hook.
#
# Opt-in per project: acts ONLY when a .riggs/ store already exists (created by
# `agent-riggs init`), so it never litters .riggs/ into projects that haven't
# opted in. When active it (1) ingests accumulated sibling-tool telemetry so the
# store is current, then (2) surfaces the cross-session briefing as
# additionalContext — making riggs ambient instead of relying on an agent
# choosing to invoke a background CLI mid-task.
#
# SECURITY: the briefing is *cross-session* content — it can carry text derived
# from prior untrusted tool outputs or repo files. It is therefore piped through
# briefing_guard.py, which normalizes it, redacts instruction-shaped lines, and
# fences it as explicitly untrusted DATA before it reaches the agent. Never
# inject `agent-riggs brief` output directly.
#
# Synchronous ingest keeps the briefing current; the 30s hook timeout bounds it.
# (If ingest ever grows slow, make it incremental in agent-riggs — see inbox.)

[ -d ".riggs" ] || exit 0

RIGGS="$(command -v agent-riggs 2>/dev/null || echo "$HOME/.local/bin/agent-riggs")"
[ -x "$RIGGS" ] || exit 0

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD="$HERE/briefing_guard.py"
# Fail closed: no guard, no briefing injection.
[ -f "$GUARD" ] || exit 0

"$RIGGS" ingest >/dev/null 2>&1
"$RIGGS" brief 2>/dev/null | python3 "$GUARD"
exit 0
