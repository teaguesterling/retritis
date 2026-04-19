#!/bin/bash
# blq: warn when agent runs build/test commands through Bash instead of blq
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

BUILD_OPS="pytest|python -m pytest|make |cargo (build|test)"
BUILD_OPS="$BUILD_OPS|npm test|npm run|yarn test"
BUILD_OPS="$BUILD_OPS|ruff |mypy |flake8 |eslint "
if echo "$COMMAND" | grep -qE "^($BUILD_OPS)"; then
  MSG="blq can capture this. Use mcp__blq_mcp__run(command=...)"
  MSG="$MSG or mcp__blq_mcp__exec(command=...) instead of Bash."
  MSG="$MSG Output is indexed and queryable."
  echo "$MSG" >&2
  exit 0
fi

exit 0
