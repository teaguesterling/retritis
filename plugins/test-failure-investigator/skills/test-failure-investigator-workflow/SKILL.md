---
name: test-failure-investigator-workflow
description: Multi-tool root-cause investigation for failing tests. Triggers on "a test failed", "the tests are failing", "investigate this test failure", "why is X test failing", "debug the failing test", "root-cause this failure", "what broke the build", "find what regressed", "tests broke after my change". Routes a Claude Code agent through the full retritis suite — jetsam branches the work, blq captures + structures the failure, squackit (over sitting_duck/fledgling) extracts the test code and traces called functions, history surfaces the last green run, structural diff narrows to what *changed*, lackpy optionally delegates mechanical composition, a subagent investigates with the full context bundle, jetsam saves the fix, blq re-runs — iterate until green. Use this skill when the request is "the suite is failing and I want it explained and fixed," NOT when it's "run the tests" (use blq directly for that).
version: 1.0.0
---

# test-failure-investigator — orchestrate the suite to root-cause a failing test

This skill teaches the cross-tool sequence that turns a red test into a green
test by composing **jetsam → blq → squackit → (lackpy) → subagent → jetsam →
blq**. Each tool already has its own skill; this one is the *recipe* that
makes them land together.

The retritis suite is much stronger when used compositionally than when any
single tool is used standalone. squackit beats grep on cross-file structure
queries, but its biggest wins come when its output feeds lackpy or a
subagent. blq beats `pytest | tail` on captured-history, but its biggest
wins come when its event refs feed squackit. This skill is the contract
between those wins.

## When this skill fires

- The user says something like "tests are failing — figure out why"
- A `blq run` returns `status="failure"` and the next step is investigation
- A subagent reports a test failure and the parent agent has to diagnose
- The user pastes a pytest traceback and asks for root cause

Do NOT fire on bare "run the tests" — that's a one-shot `mcp__blq_mcp__run`
and you go straight back to the user.

## The sequence at a glance

| # | Step (user's framing)              | Tool                                                                                  |
|---|------------------------------------|---------------------------------------------------------------------------------------|
| 1 | a test failed                      | trigger (blq event, traceback, or user message)                                       |
| 2 | jetsam starts a new branch         | `mcp__jetsam__start(target="fix-<short-name>")` → `confirm`                           |
| 3 | blq parses out the test failure    | `mcp__blq_mcp__events(severity="error")` → `mcp__blq_mcp__inspect(ref=...)`           |
| 4 | squackit extracts the test code    | `mcp__plugin_squackit_squackit__investigate(name=<test_fn>, path=<repo>)`             |
| 5 | lackpy writes selectors for called fns | `mcp__plugin_lackpy_lackpy__delegate(intent=...)` OR write selectors inline           |
| 6 | blq has the last passing version   | `mcp__blq_mcp__history(limit=20)` → find last `status="success"` ref                  |
| 7 | identify what changed since then   | `mcp__plugin_squackit_squackit__file_changes(from_rev=<last_green>, to_rev="HEAD")`   |
| 8 | squackit pulls changed functions   | `mcp__plugin_squackit_squackit__changed_function_summary(from_rev=..., to_rev=...)`   |
| 9 | bundle context → investigate       | `mcp__plugin_lackpy_lackpy__delegate(...)` OR pack a context string for the subagent  |
| 10 | spawn subagent to investigate     | `Agent(subagent_type="general-purpose", prompt=<bundle>)`                             |
| 11 | jetsam saves the fix              | `mcp__jetsam__save(message=...)` → `confirm`                                          |
| 12 | blq re-runs the tests             | `mcp__blq_mcp__run(command="test")` — loop to step 3 if still red                     |

## The recipe — step by step

### 1. Identify the failure

If the trigger was the user pasting a traceback, you have file + line +
exception. If you only know "the tests are failing," capture them first:

```
mcp__blq_mcp__run(command="test", lines="+30-")   # run + return last 30 lines inline
mcp__blq_mcp__events(severity="error")             # structured failure events
```

Pick the first failing test and grab its event ref (e.g. `test:1:3`).

### 2. Branch the work

Always investigate on a branch — fixes may take several iterations and you
want a clean rollback path:

```
plan = mcp__jetsam__start(target="fix-failing-<test_name>")
mcp__jetsam__confirm(id=plan["id"])
```

Pass `cwd=` if the failing repo is not the current process cwd (jetsam
33d5869+).

### 3. Pull the structured failure detail

```
mcp__blq_mcp__inspect(ref="test:1:3")
```

This returns log lines, the offending source snippet, and git context for
the event. Note the file path and the test function name — these feed
step 4.

### 4. Extract the test code and its call sites

```
mcp__plugin_squackit_squackit__investigate(
    name="<test_fn>",
    path="/path/to/repo",         # explicit, since cf36894 — beats cwd-leak
)
```

`investigate` returns: definition + source + callers + callees in one call.
The "Calls" table is what step 7's diff narrows against.

For test fixtures or helpers the failing test depends on, follow up with:

```
mcp__plugin_squackit_squackit__find(
    source="**/conftest.py",
    selector=".fn#<fixture_name>",
)
```

### 5. Trace called functions (optionally via lackpy)

If `investigate` named N callees, you want each one's definition. Two ways:

**Inline** (Claude composes selectors directly — fast for ≤5 callees):

```
for fn_name in callees:
    mcp__plugin_squackit_squackit__find_names(
        source="**/*.py",
        selector=f".fn#{fn_name}",
    )
```

**Delegated** (lackpy generates a program — for ≥10 callees so Claude
doesn't burn context on the loop):

```
mcp__plugin_lackpy_lackpy__delegate(
    intent="for each function in [list], use squackit to find its definition and source",
    kit="squackit",
)
```

If no `selector_writer` lackpy kit is registered, fall back to inline.
Selector grammar reference is short enough to hand-write:

```
.fn#foo           # function named foo
.cls#Bar          # class named Bar
.call#foo         # call sites of foo (any receiver)
.call#foo[receiver="duckdb"]   # only duckdb.foo() — receiver is qualified
.fn:has(.call#foo)              # functions that call foo
```

(`[receiver=X]` was added in squackit#4. Operators `=`, `*=`, `^=`, `$=`.
A bare call like `foo()` has `receiver=""` — won't match a non-empty value.)

### 6. Find the last passing run

```
mcp__blq_mcp__history(limit=20)
```

Walk the list backward to the most recent `status="success"` run for the
test command. Note its git SHA (`info(ref=...)` exposes commit metadata if
not in the history row directly).

### 7. Identify what changed since the last green

```
mcp__plugin_squackit_squackit__file_changes(
    from_rev=<last_green_sha>,
    to_rev="HEAD",
)
```

Intersect with the callees from step 4/5 — the callees that *also* appear in
the changed-files list are your suspect set.

For semantic detail (added/removed/modified definitions, not just file
names):

```
mcp__plugin_squackit_squackit__structural_diff(
    file="<callee_file>",
    from_rev=<last_green_sha>,
    to_rev="HEAD",
)
```

### 8. Pull the changed functions with diffs

```
mcp__plugin_squackit_squackit__changed_function_summary(
    from_rev=<last_green_sha>,
    to_rev="HEAD",
    file_pattern="<glob if you want to scope>",
)
```

This ranks by complexity, so the riskiest changes are first.

For a raw line-level view:

```
mcp__plugin_squackit_squackit__file_diff(
    file=<suspect_file>,
    from_rev=<last_green_sha>,
    to_rev="HEAD",
)
```

### 9. Bundle the context

Pack what you've collected into a single context blob:

- The failing test name + failure event (step 3)
- The test source (step 4)
- The callee definitions (step 4/5)
- The "what changed since last green" set (step 7/8)
- Diffs of the suspect changes (step 8)

You have two delivery options:

**Lackpy** (when the investigation is mechanical — match exception against
diff lines, find the symbol that disappeared, etc.):

```
mcp__plugin_lackpy_lackpy__delegate(
    intent="given test source X, exception Y, and diff Z, identify which diff line broke the test",
    kit="text",
)
```

**Subagent** (when judgment is required — choose between two fixes, decide
whether the test or the code is wrong, weigh tradeoffs):

→ go to step 10.

### 10. Spawn an investigation subagent

Use the `Agent` tool. The subagent gets the bundle but NOT this
conversation, so the prompt must be self-contained:

```
Agent(
    description="Root-cause failing test",
    subagent_type="general-purpose",
    prompt=f"""
A test is failing and the surrounding context is below. Your job is to
identify the root cause and propose a fix.

## Failing test
{test_source_from_step_4}

## Exception
{event_inspect_from_step_3}

## What changed since the last green run ({last_green_sha[:8]} → HEAD)
{changed_function_summary_from_step_8}

## Diffs of the suspect changes
{file_diff_from_step_8}

Return:
1. Root cause (one paragraph)
2. Proposed fix (file path + diff or replacement code)
3. Confidence (low / medium / high) and what would raise it
""",
)
```

For a more targeted investigation (e.g., "verify my hypothesis"), use
`subagent_type="general-purpose"` with a narrower prompt. For broad
codebase exploration before the bundle is ready, use `subagent_type="Explore"`.

### 11. Save the fix

After applying the subagent's proposed fix (with your judgment — don't
auto-apply low-confidence suggestions):

```
plan = mcp__jetsam__save(message="fix: <one-line of what>")
mcp__jetsam__confirm(id=plan["id"])
```

### 12. Re-run the tests

```
mcp__blq_mcp__run(command="test", lines="+30-")
```

- **Green:** ship via `mcp__jetsam__ship(message="...")` or push and open
  PR via `mcp__jetsam__sync` then `pr_view`.
- **Still red:** check `mcp__blq_mcp__diff(run1=<prev_red>, run2=<current>)`
  — if the error fingerprint *changed*, you fixed one problem and uncovered
  another (loop back to step 3 with the new failure). If the error
  fingerprint is *the same*, your fix didn't take effect (loop back to step
  9 with the new evidence).

## Variations and fallbacks

### No last green run in blq history
The `blq history` only covers what's been run locally through blq. If
there's no recorded green run, fall back to git: use `git log` (via
`mcp__plugin_jetsam_jetsam__log`) on the test file or the suspect callees
and pick a SHA before the offending change. For step 7, use that SHA.

### Selector kit unavailable
If lackpy has no `selector_writer` or `squackit` kit registered, do step 5
inline — the selector grammar is small enough that hand-writing 5-10
selectors is faster than the kit-setup detour.

### The test is in a different repo from the cwd
Pass `cwd=` to every jetsam verb and `path=` (or scoped `file_pattern=`)
to squackit's `investigate` — both were fixed for cross-repo investigation
in jetsam 33d5869 and squackit cf36894. Without these, jetsam will commit
on the *current* repo's branch and squackit will substring-match symbols
across every indexed project.

### Multiple tests are failing
Investigate the *first* failure — it's often the root cause and the rest
are cascade failures. After applying a fix, re-run; if N-1 of N now pass,
you're done. If multiple unrelated tests fail, treat each as a separate
investigation (one branch each, or one branch with each fix as a separate
`save`).

### The failure is environmental, not in code
If the diff (step 8) is empty or unrelated, suspect the environment —
recent dep updates, flaky external services, clock skew. `blq diff` between
the red run and a recent green run can show whether the failure fingerprint
matches a known flake. Document and re-run before assuming a code fix.

## Worked example (compressed)

```
# 1. capture
mcp__blq_mcp__run(command="test")
# → run 47, 1 failure: tests/test_workflows.py::TestInvestigate::test_scopes_to_project_by_default

# 2. branch
mcp__jetsam__start(target="fix-investigate-scoping") → confirm

# 3. inspect
mcp__blq_mcp__inspect(ref="test:47:1")
# → AssertionError: investigate leaked across project boundaries

# 4. extract test + callees
mcp__plugin_squackit_squackit__investigate(name="test_scopes_to_project_by_default",
                                           path="/home/teague/Projects/squackit")
# → callee: investigate (in workflows.py)

# 5. trace
mcp__plugin_squackit_squackit__investigate(name="investigate",
                                           path="/home/teague/Projects/squackit")
# → uses defaults.code_pattern (global), not scoped_code_pattern(cwd)

# 6. last green
mcp__blq_mcp__history(limit=20) → run 39 was green, SHA abc123

# 7-8. what changed
mcp__plugin_squackit_squackit__changed_function_summary(from_rev="abc123", to_rev="HEAD")
# → investigate() touched recently; defaults.code_pattern unchanged

# 9-10. bundle + subagent
Agent(description="...", prompt="...")
# → root cause: investigate() should accept a path= argument and call
#   scoped_code_pattern(path or cwd) instead of code_pattern

# 11-12. fix + re-run
# (apply patch)
mcp__jetsam__save(message="investigate: accept path arg, scope to cwd by default") → confirm
mcp__blq_mcp__run(command="test")
# → green, ship
```

## What this skill is NOT

- Not a replacement for blq-workflow / squackit-workflow / jetsam-workflow
  — those describe each tool's full surface. This skill describes the
  *sequence* across them for one specific recurring task.
- Not a fully automated loop — judgment lives in step 9 (which channel:
  lackpy or subagent?) and step 12 (ship, iterate, or escalate?). Don't
  delete the human-in-the-loop checkpoints.
- Not the right skill for "the build is slow" or "this test is flaky but
  passes on retry" — those are different shapes (perf investigation,
  flake-rate analysis) and warrant their own skills.
