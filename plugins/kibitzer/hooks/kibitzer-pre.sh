#!/usr/bin/env bash
# kibitzer PreToolUse hook — on-the-fly coaching.
# Resolve the interpreter that runs the `kibitzer` console script (its shebang
# points at the env where kibitzer is installed), so this works regardless of
# venv activation. Falls back to python3.
PY="$(sed -n '1s/^#!//p' "$(command -v kibitzer 2>/dev/null)" 2>/dev/null)"
exec "${PY:-python3}" -m kibitzer.hooks.pre_tool_use
