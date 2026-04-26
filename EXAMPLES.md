# Clinical Examples

*Case studies from the field. Each demonstrates how retritis components compose to treat a specific symptom.*

---

## Case 1: The bug that explains itself

**Presenting symptom:** A test fails. You paste the traceback into chat. Claude asks for context. You paste more. Claude asks for the file. You paste the file. Three rounds of copy-paste before anyone starts thinking about the bug.

**Treatment:**

```bash
# Run the tests through blq — results are captured, not printed-and-forgotten
$ blq run test

# Claude checks the structured results directly (MCP tool call)
blq.errors()
# → [{ file: "src/auth.py", line: 47, error: "TypeError: expected str, got None",
#        test: "test_validate_token", traceback: [...] }]

# Claude uses the error to find the code — squackit resolves structure
squackit.find_definitions("src/auth.py", ".fn#validate_token")
# → function validate_token(token): lines 32-58
#   calls: decode_jwt (src/jwt.py:12), check_expiry (src/auth.py:60)
#   called_by: login_handler (src/routes.py:85), refresh_handler (src/routes.py:112)

# Claude checks what changed recently
duck_tails.file_history("src/auth.py", limit=5)
# → commit a3f2b1c (2 days ago): "refactor: make decode_jwt return Optional"
#   changed lines: 38-42 (validate_token body)
```

**What happened:** Three tools composed without coordination. blq captured the error as structured data. squackit resolved the function's context — definition, callers, callees. duck_tails found the recent change that likely introduced the bug. Claude never asked "can you paste the file?" because every fact was one query away.

**Without retritis:** 3-5 rounds of copy-paste, manual file navigation, `git log --follow` piped through grep. Same diagnosis, four times the friction.

---

## Case 2: The refactor with a blast radius

**Presenting symptom:** You need to rename a function used across 40 files. Find-and-replace breaks things because some call sites pass different argument shapes. You need to understand the blast radius before you change anything.

**Treatment:**

```bash
# Map the blast radius
squackit.find_callers("src/db.py", ".fn#execute_query")
# → 47 call sites across 23 files
#   12 pass positional args, 35 pass keyword args
#   3 use **kwargs forwarding

# Find structurally similar functions (candidates for the same refactor)
squackit.find_similar("src/db.py", ".fn#execute_query")
# → execute_query_async (src/db.py:89) — 0.92 similarity
#   run_query (src/legacy.py:34) — 0.78 similarity

# Use pluckit to do the rename with type-aware argument updates
select('.fn#execute_query, .fn#execute_query_async')
    .rename('run_sql')
    .callers()
    .replaceWith('execute_query(', 'run_sql(')
    .replaceWith('execute_query_async(', 'run_sql_async(')
    .test()
    .save('refactor: rename execute_query → run_sql')
```

**What happened:** squackit mapped every call site and found similar functions that should be renamed together. pluckit performed the rename as a single chain — including finding all callers, updating call sites, running tests, and committing. The chain is one logical operation, not 40 manual edits with a prayer.

**The ratchet turn:** agent-riggs records this trace. Next time someone renames a function, the pattern — map callers, find similar, rename together, update call sites, test, save — is available as a template. The second rename is faster than the first.

---

## Case 3: The error that fixes itself

**Presenting symptom:** The same category of bug keeps appearing — a function that returns `None` when the caller expects a string. Different functions, same pattern.

**Treatment (first occurrence):**

```bash
# blq captures the error as a structured event
blq.errors()
# → [{ id: "build:42:err_7", error: "TypeError: expected str, got None",
#        file: "src/auth.py", line: 47, function: "validate_token" }]

# Fix it with a pluckit chain, starting from the error event
blq.event('build:42:err_7')
    .select()                              # selects the failing code
    .replaceWith(
        'return None',
        'raise ValueError("token invalid")'
    )
    .test('tests/test_auth.py')
    .save('fix: validate_token raises instead of returning None')
```

**Treatment (second occurrence, two weeks later):**

```bash
# agent-riggs recognizes the pattern
riggs.fingerprints()
# → [{ pattern: "TypeError: expected str, got None",
#        fix_chain: "select().replaceWith('return None', 'raise ValueError(...)')",
#        confidence: 0.85, occurrences: 3 }]

# The fix applies automatically — no model call needed
blq.event('build:58:err_3')
    .select()
    .replaceWith('return None', 'raise ValueError("invalid input")')
    .test()
    .save('fix: handle None return (auto-fingerprint)')
```

**What happened:** The first fix was manual — a developer wrote the pluckit chain. agent-riggs recorded the trace: error pattern → fix chain → success. When the same error pattern appeared again, the fix was already known. No LLM call, no human intervention. The error fixed itself.

**The ratchet:** `observation → trace → fingerprint → template → automatic fix`. Each occurrence strengthens the fingerprint. After enough occurrences, the fix drops to Tier 0 — pure template application, zero cost.

---

## Case 4: The codebase tour

**Presenting symptom:** New to a project. You need to understand the architecture before you can contribute. Reading files one at a time is slow. Grepping for patterns misses structure.

**Treatment:**

```bash
# Get the high-level structure
squackit.code_structure("src/", depth=2)
# → src/
#     api/          — 12 files, 45 functions, 8 classes
#       routes.py   — FastAPI router, 15 endpoints
#       middleware.py — 3 middleware classes
#       deps.py     — dependency injection
#     core/         — 8 files, 32 functions, 5 classes
#       auth.py     — authentication logic
#       db.py       — database layer
#       cache.py    — Redis wrapper
#     models/       — 6 files, 18 classes
#     utils/        — 4 files, 22 functions

# Find the entry points — exported functions are the public API
squackit.find_definitions("src/api/", ".fn:exported")
# → 15 route handlers, each with decorator metadata

# Trace a specific request path
squackit.find_callees("src/api/routes.py", ".fn#create_user")
# → create_user calls:
#     validate_input (src/core/auth.py:23)
#     hash_password (src/core/auth.py:45)
#     db.insert_user (src/core/db.py:67)
#     send_welcome_email (src/utils/email.py:12)

# Check what's been changing — where is the project's attention?
duck_tails.hot_files(days=30)
# → src/core/auth.py      — 23 commits (most active)
#   src/api/routes.py      — 18 commits
#   src/core/db.py         — 12 commits
#   tests/test_auth.py     — 11 commits
```

**What happened:** Four queries, and you have: the module layout, the public API, a traced request path, and where recent work has concentrated. The agent now has a reliable mental model — not from reading files linearly, but from querying structure.

**Without retritis:** Claude greps for `def `, reads 6-8 files, builds an approximate picture, misses the call graph, doesn't know what's been changing. Same 15 minutes of context gathering, less accurate result.

---

## Case 5: Policy in one place

**Presenting symptom:** Your agent can edit any file, run any command, call any tool. You want boundaries — but they're configured in five places: CLAUDE.md, hooks, nsjail profiles, MCP server permissions, file system mounts. When you change a policy, you update three configs and forget the fourth.

**Treatment:**

```yaml
# delegate.world.yml — declare what exists
tools: [Read, Edit, Bash, Write]
modes: [implement, review]
principal: Teague

entities:
  - type: tool
    id: Bash
    classes: [dangerous]
```

```css
/* policy.umw — one file, all boundaries */

/* Default: everything visible and allowed */
tool { visible: true; allow: true; max-level: 8; }

/* Dangerous tools are capped */
tool.dangerous { max-level: 3; }

/* In review mode, most tools are denied */
mode#review tool { allow: false; }
mode#review tool#Read { allow: true; }

/* Source code is editable in implement mode */
mode#implement file:glob("src/**/*.py") { editable: true; }

/* Tests are always editable */
file:glob("tests/**") { editable: true; }

/* Principal-gated: Teague gets extra visibility */
principal#Teague tool { visible: true; }
```

```python
from umwelt.policy import PolicyEngine

engine = PolicyEngine.from_files(
    world="delegate.world.yml",
    stylesheet="policy.umw",
)

# What does the policy say?
engine.resolve(type="tool", id="Bash", property="max-level")
# → "3"

# Context qualifiers gate by mode, principal, or any cross-taxon entity
engine.resolve(
    type="tool", id="Bash", property="allow",
    context={"mode": "review"},
)
# → "false"

# Why did that value win? Full audit trail.
trace = engine.trace(type="tool", id="Bash", property="allow",
                     context={"mode": "review"})
# → Winner: "false" (spec=[0,1,1] rule=2 policy.umw:8)
#   Runner-up: "true" (spec=[0,0,1] rule=1 policy.umw:4)

# Each consumer queries its own slice:
#   kibitzer: engine.check(type="tool", id="Bash", allow="true")
#   sandbox:  engine.resolve_all(type="dir")
#   lackpy:   engine.resolve_all(type="tool")
# Same compiled database, different consumers reading different views.
```

**What happened:** One world file declares what exists. One stylesheet declares the rules. umwelt compiles both to SQLite, resolves the cascade (specificity + document order, per-property, per-entity), and the PolicyEngine answers queries. Each consumer — kibitzer, lackpy, a sandbox builder — asks the PolicyEngine what the resolved policy says, and acts on the answer. Nobody touches the parser or compiler. Change the policy in one place, every consumer picks it up.

**The key insight:** Cross-taxon selectors like `mode#review tool` and `principal#Teague tool` are generic context qualifiers, not hardcoded special cases. The same mechanism works for any entity type used as a gating condition — mode, principal, world environment, or anything a consumer registers. Core umwelt is vocabulary-agnostic; all entity types come from consumers via the registry.

**The disconnect this solves:** "The agent inherits the user's permissions" (principal side), "the tool is restricted to these operations" (action side), "the file system is mounted read-only" (resource side) — three separate discussions that are actually one policy question. umwelt makes it one answer. See the [Policy Layer](https://judgementalmonad.com/blog/policy/) series for the full argument.

---

## Case 6: The session that recovers itself

**Presenting symptom:** Claude crashes mid-task. You had unsaved work in the conversation. The session state is scattered across temp files, conversation logs, and uncommitted git changes. Reconstructing where you were takes longer than the work itself.

**Treatment:**

```bash
# ffs finds the failed session and reconstructs context
$ ffs
Found 1 failed session (crashed 12 minutes ago):
  Session: a3f2b1c4
  Duration: 47 minutes
  Last tool: Edit (src/core/auth.py, line 45)
  Uncommitted changes: 3 files
    M src/core/auth.py
    M tests/test_auth.py
    A src/core/token_validator.py

  Conversation summary (from fledgling):
    - User asked to add token validation
    - Claude created token_validator.py
    - Claude was editing auth.py to integrate it
    - Last message: "Now I'll update the tests..."

  Recovery options:
    1. Resume: start new session with context summary attached
    2. Stash: save uncommitted changes to a recovery branch
    3. Review: open diff of uncommitted changes

$ ffs resume
# → starts new Claude session with the context summary as the first message
# → Claude picks up where it left off, no re-explanation needed
```

**What happened:** ffs read the conversation log (via fledgling's conversation tables), checked git state, and reconstructed what was happening when the crash occurred. The recovery option injects the summary into a new session so the new Claude instance has full context. No manual reconstruction.

**The composition:** fledgling provides conversation history as queryable data. git provides the uncommitted changes. ffs joins them into a recovery plan. The tools weren't designed for crash recovery together — but because they share the DuckDB substrate, the join is trivial.

---

## Case 7: Teaching the model your API

**Presenting symptom:** You have a tool with a well-defined API (pluckit, an internal DSL, a domain-specific library). The frontier model uses it correctly 70% of the time. You want 95%+. Fine-tuning a frontier model is expensive and slow.

**Treatment:**

```bash
# Generate training data from the API spec — no usage data needed yet
$ lackpy generate-training \
    --spec pluckit-api.json \
    --intents 1000 \
    --output training-pairs.jsonl

# Each pair: natural language intent → valid API call
# {"intent": "add a timeout parameter to all public functions",
#  "chain": "select('.fn:exported').addParam('timeout: int = 30').test().save('feat: add timeout')"}

# Fine-tune a small local model
$ lackpy train \
    --base qwen2.5-coder-3b \
    --data training-pairs.jsonl \
    --method qlora \
    --output models/pluckit-specialist

# The specialist runs locally, $0 per call
$ lackpy infer --model models/pluckit-specialist \
    "find functions that nobody calls anymore"
# → select('.fn').filter(fn => fn.callers().count() === 0)
```

**The three-tier cascade:**

| Tier | Provider | Cost | When |
|------|----------|------|------|
| **Tier 0** Templates | Exact match from agent-riggs | $0, instant | Pattern seen ≥5 times |
| **Tier 1** Local model | Fine-tuned 3B via Ollama | $0, ~200ms | Known API, novel intent |
| **Tier 2** Frontier | Claude/GPT via API | $$, ~2s | Complex reasoning needed |

**The ratchet:** Every successful Tier 2 call produces a trace. Traces that recur get promoted to Tier 0 templates. The fine-tuned Tier 1 model handles the middle — intents that aren't exact matches but don't need frontier reasoning. Over time, Tier 2 calls decrease. Cost converges toward zero for routine operations.

---

## Dosage

Start with the minimum effective dose:

**Acute symptoms (start here):**
- `blq` — if you're copy-pasting build output
- `jetsam` — if git ceremony is eating your time
- `squackit` — if Claude keeps grepping instead of understanding

**Chronic symptoms (add when ready):**
- `kibitzer` — if you want the tools to coach toward better patterns
- `agent-riggs` — if you want cross-session learning
- `pluckit` — if you want fluent code mutation chains

**Experimental treatment (when you're ready for the theory):**
- `umwelt` — if you want unified policy with the PolicyEngine API. Declare entities in a world file, write rules in CSS syntax, query resolved policy through `engine.resolve()`. Generic context qualifiers let you gate rules on mode, principal, or any cross-taxon entity.
- `lackpy` — if you want a local model that knows your APIs

The tools are independent. Install one, install all, install them in any order. The composition emerges from the shared substrate, not from a required install sequence.
