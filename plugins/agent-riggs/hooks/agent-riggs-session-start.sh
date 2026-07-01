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
# Synchronous ingest keeps the briefing current; the 30s hook timeout bounds it.
# (If ingest ever grows slow, make it incremental in agent-riggs — see inbox.)

[ -d ".riggs" ] || exit 0

RIGGS="$(command -v agent-riggs 2>/dev/null || echo "$HOME/.local/bin/agent-riggs")"
[ -x "$RIGGS" ] || exit 0

"$RIGGS" ingest >/dev/null 2>&1
brief="$("$RIGGS" brief 2>/dev/null | tr -cd '\11\12\40-\176')"
[ -n "$brief" ] || exit 0

python3 - "$brief" 2>/dev/null <<'PY'
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "agent-riggs cross-session briefing (this project):\n" + sys.argv[1],
    }
}))
PY
exit 0
