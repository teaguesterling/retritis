---
name: kibitzer-workflow
description: Kibitzer observes your tool usage and suggests improvements — let it watch
---

## What kibitzer does

Kibitzer watches your tool calls and suggests structured alternatives when it sees patterns that have better options.

Examples:
- "You've searched for this function three times — try `find_callers` instead."
- "You've made 5 edits without running tests — consider running the test suite."
- "This grep pattern matches a squackit selector — try `find_names`."

## How to use

Kibitzer runs passively. It observes and suggests. Suggestions are not enforcement — ignore them when they don't apply.

Follow rates are tracked. If you consistently ignore a suggestion type, kibitzer stops making it. If you consistently follow one, it may promote the pattern to a strategy instruction.

## The feedback loop

Observations → suggestions → follow/ignore → adjusted thresholds → better suggestions. The ratchet's observation phase, automated.
