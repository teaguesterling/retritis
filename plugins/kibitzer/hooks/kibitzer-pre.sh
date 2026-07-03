#!/usr/bin/env bash
# kibitzer PreToolUse hook — on-the-fly coaching.
#
# POSTURE: advisory and fail-open BY DEFAULT. If kibitzer isn't importable,
# the guard is SKIPPED — with a visible warning, never silently — and the
# tool call proceeds. Set RETRITIS_FAIL_CLOSED=1 to invert that: a missing/
# broken kibitzer then blocks tool calls (exit 2) until the install is fixed.
# See README "Trust model & enforcement posture".
#
# Resolve the interpreter that runs the `kibitzer` console script (its shebang
# points at the env where kibitzer is installed), so this works regardless of
# venv activation. Falls back to python3. KIBITZER_PYTHON overrides (tests).
PY="${KIBITZER_PYTHON:-$(sed -n '1s/^#!//p' "$(command -v kibitzer 2>/dev/null)" 2>/dev/null)}"
PY="${PY:-python3}"

if ! "$PY" -c 'import kibitzer' 2>/dev/null; then
    if [ "${RETRITIS_FAIL_CLOSED:-0}" = "1" ]; then
        echo "kibitzer guard unavailable and RETRITIS_FAIL_CLOSED=1 — blocking tool call" >&2
        exit 2
    fi
    echo "kibitzer not importable — advisory guard skipped (fail-open; set RETRITIS_FAIL_CLOSED=1 to block instead)" >&2
    exit 0
fi

exec "$PY" -m kibitzer.hooks.pre_tool_use
