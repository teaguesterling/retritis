#!/bin/bash
# jetsam: warn when agent uses raw git/gh instead of JetSam MCP tools
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

GIT_OPS="commit|push|add|merge|rebase|fetch|stash|checkout|switch"
if echo "$COMMAND" | grep -qE "^git\s+($GIT_OPS)"; then
  MSG="JetSam has tools for this."
  MSG="$MSG Use save (commit), sync (push/fetch/merge),"
  MSG="$MSG ship (commit+push+PR), start/switch (branching)"
  MSG="$MSG instead of raw git."
  echo "$MSG" >&2
  exit 0
fi

if echo "$COMMAND" | grep -qE '^gh\s+(pr|issue|release|run)'; then
  MSG="JetSam has tools for GitHub operations."
  MSG="$MSG Use pr_view, pr_list, pr_comment, pr_review,"
  MSG="$MSG checks, issues, issue_close, ship, or release"
  MSG="$MSG instead of gh CLI."
  echo "$MSG" >&2
  exit 0
fi

exit 0
