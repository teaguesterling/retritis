---
name: lackpy-delegation
description: How to hand real work to a local small model through lackpy without wasting the round trip. Use when delegating to lackpy/Tiiny/Ollama — "have the local model fix this", "delegate this to lackpy", "offload this to the device", "run this on the small model" — and whenever a lackpy delegation returns None, an empty program, an invented file path, or a plausible-looking wrong answer. Covers what the caller must supply (procedure, return shapes, the implicated source file), how far up the context ladder a task has to be carried before it succeeds, which invocation form actually works, and the failure modes that look like model weakness but are not. This is the CALLER's half of the contract; lackpy-workflow covers the tool surface.
version: 1.0.0
---

# Delegating to a local model through lackpy

Everything here is measured against a seeded repo with a real failing test,
graded by running pytest. Numbers are trial counts, not impressions.

## The one rule

> **Delegate execution, not diagnosis.**

The local model reliably *applies and verifies* a decision. It cannot *form* one
inside a single generated program — not because it is weak, but because lackpy
generates the whole program before running any of it, and a repair needs a string
that only exists after a file has been read.

| what you ask | result |
|---|---|
| "change `LEVELS.get(value)` to `LEVELS.get(value, DEFAULT_LEVEL)`" | passes on every model |
| "a test is failing, work out why and fix it" | **0/5** |
| the same, with the file's text in the prompt | **5/5** |

So: you decide what changes. It edits, runs, commits, reports.

And whatever you delegate, **never grade it by reading its answer.** Run the
tests, read `git log`, open the file. Several mechanisms in this stack report
success having done nothing — `save()` without `confirm()` returns a valid
program, no error, and a plausible plan dict, and commits nothing.

> **Version sensitivity.** v0.15.1 is the current release, and lines marked
> *(lackpy ≤ 0.15.1)* are still live in it. The fixes exist only on the unreleased
> `mcp-tool-metadata` branch, so on anything you can `pip install` today these
> caveats **apply**. They are written so the advice is safe either way — following
> it costs nothing after the fix lands. Re-check the three against your installed
> version rather than assuming; an earlier draft of this file carried a made-up
> version number, which is the failure this note now exists to prevent.

## You must supply three things. Missing any one fails.

Measured as a ladder — each rung is a real suite call, crossed with whether the
intent carries a procedure. The failure mode is *different* at each rung, which
is how you tell which piece you left out.

| you gave it | it fails with |
|---|---|
| nothing but "a test is failing" | `Parse error: unterminated string literal (line 1)` — it wrote prose |
| a procedure, but no source path | `[Errno 2] No such file or directory: 'src/priority.py'` — invented |
| a path, but not the file's contents | `String containing '__' … forbidden` — invented a body |
| **procedure + path + contents** | **passes** |

**1. The procedure.** One sentence, and it removes the entire parse-error class:

> "Emit ONLY the `edit_file` call followed by `run(command='test')` — do not
> redefine any function, and copy `old_str` exactly from the text above so it
> matches character-for-character."

Without it, even handing over the complete file scores 0/3. Information alone
moves nothing.

**2. The implicated source file — by name.** Resolve it yourself; do not assume
the failure event carries it.

For a **single-frame assertion failure** — the common case, and the one where
delegation is most attractive — blq's `ref_file` is the *test* file, because the
traceback contains no other frame. Hand that over and the model must guess where
the implementation lives; it guesses wrong every time. For a **multi-frame**
failure it is usually right: duck_hunt's pytest parser keeps the *last*
`file.py:NN:` location in the failures block, deliberately, so a
test → helper → raise chain yields `src/mylib/checks.py:2`. Verified both ways.

`pytest_json` always reports the `nodeid` prefix and never sets `ref_line`, so it
is always the test. `squackit.view` **renders markdown** — `file:range` headings
around fenced code — so it shows you the path but does not hand a program a path
it can use. Inside a generated program prefer `find`/`find_names`, which return
structured results; save `view` for output a human reads.

**3. The file's current text.** Any operation whose payload derives from current
state cannot be written by a program that has not yet read that state. This is
not fixed by selector-addressed APIs: given `ast_replace(selector='.fn#name',
new_text=…)`, which removes the need to quote the old text, the model invents the
*body* instead and reproduces the bug it was asked to fix.

## Invocation

```bash
lackpy --workspace "$REPO" -c "$INTENT" --profile fix
```

Ship these profiles into **`$REPO/.lackpy/kits/`** (they are in this plugin's
`profiles/`): `fix`, `diagnose`, `ship`, `report`, `explore`.

This is **per target repo, not per user**. `kits_dir` is `config_dir / "kits"` and
`config_dir` is strictly `workspace / ".lackpy"` with no global fallback, so
`~/.lackpy/kits/` is never consulted and copying them there once gives you
`FileNotFoundError` in every repo. The same goes for `config.toml`: a `$REPO`
without its own gets `order = ["templates", "rules"]` — no LLM tier at all.

If you name tools inline instead, **use `--profile none --tools a,b`**. Three
silent traps otherwise:

| what you write | what happens |
|---|---|
| `--profile log` | a bare token is a profile *name*, not a tool. On ≤ 0.15.1 this raises `FileNotFoundError` out of `_load_tools_file` — an uncaught traceback, not a clean error. `919b3da` turns it into a message naming the fix |
| *(omit `--profile`)* | not "all tools" — the built-in default is a `debug` profile that does not ship |
| `--profile none --tools log` | ✓ |

**Read the failure envelope from stderr** *(lackpy ≤ 0.15.1; fixed by `7430fd8`)*.
Success goes to stdout with exit 0; the "all providers failed" envelope goes to
**stderr with exit 1**. A caller reading stdout alone records every failed
generation as an empty program with no error. Read both streams and you are
correct on either version.

## Writing the intent

- **Say "return X."** lackpy returns the last *expression*. A program ending in
  `count = …` yields `None`.
- **Name the return shape.** *(lackpy ≤ 0.15.1; `4f5cccd` derives `returns` from the
  tool's `outputSchema`, which fixes the type half.)* Every MCP tool arrived as
  `returns="Any"`, so the model guessed, and a wrong guess still validates and
  runs. On a battery with no shapes given: **0/24 correct while 17/24 called the
  right tool.** Even after that fix, state the *keys* — fastmcp emits a keyless
  `{"type": "object"}` for dict-returning tools, so the schema can say `dict`
  without saying which key holds the answer.
- **State invariants, not just APIs.** Describing `save()`'s return left the model
  calling `save` and stopping, 4/4 trials. Adding "*both statements are required;
  save alone does not commit*" fixed it first try. A shape is a fact about one
  call; an invariant is a fact about two, and only the first survives description.
- **Do not paste source without a guard.** Injected code gets echoed into the
  program and fails validation with `Forbidden AST node: FunctionDef`.
- **Avoid "find the first match."** *(lackpy ≤ 0.15.1; `1c85284` allows
  `GeneratorExp` and `next`.)* `next(genexp)`, `any(genexp)`, `for … break` and
  iterating a subscript were all rejected, leaving only
  `[x for x in xs if …][0]` — which trips better coder models *harder*, since they
  reach for `next`. `Break`, `Continue`, `While` and `Try` are still rejected, so
  the loop-and-break form does not work on any version.

## Return shapes worth memorising

| tool | shape | `len()` gives | correct |
|---|---|---|---|
| `blq.events` | `{'events': [...], 'total_count': N}` | 2 (keys) | 1 |
| `blq.status` | `{'sources': [{...}]}` | 1 (keys) | — |
| `squackit.find_names` | one newline-joined **string** | 67 (chars) | 8 |
| `squackit.find` | a rendered **markdown table** | 2239 (chars) | 8 |
| `jetsam.log` | `list[dict]`, newest first | 5 | 5 ✓ |

jetsam and blq return real structured data. squackit returns text formatted for a
human reader — fine for you, near-useless to a program with no regex and no
imports. Prefer `find_names` (splittable) over `find` (a table).

## Verify by inspecting the world

Stated once at the top; here is what it means per outcome.

- a fix → run the tests, *and* assert the module and test file are intact, or a
  "fix" that deletes the failing test scores as a pass
- a commit → `git log`
- a written file → read it

This is not paranoia. It is the difference between a system that failed and a
system that reported success having done nothing — and the second is
indistinguishable from the first unless you look at the world.

## Configuration that changes outcomes

```toml
[inference]
order = ["llm"]          # REQUIRED: a provider not named here is never constructed.
                         # Default is ["templates", "rules"] -- no LLM tier at all.

[inference.providers.llm]
plugin   = "woollama"    # REQUIRED: service.py builds a provider only for
                         # "woollama" or "cascade". Omit it and the whole block
                         # is silently inert -- no error, just no LLM.
model    = "openai/tiiny/Qwen/Qwen3-Coder-30B-A3B-Instruct"   # explicit id, never X/default
base_url = "http://127.0.0.1:47600/v1"                        # pooled: queue, not a wedge
api_key  = "..."
params   = { max_tokens = 4096, chat_template_kwargs = { enable_thinking = false } }
```

The tier name (`llm` here) is arbitrary but must match between the two tables;
`lackpyctl init` names it `local`. Both `plugin` and the `order` entry are
load-bearing and both fail *quietly* — this block was published once without
them, which reads fine and does nothing.

- **Thinking is per-request configuration**, and the only dialect honoured is
  `chat_template_kwargs.enable_thinking`. Worth 33× on a reasoning model
  (23.1s → 0.7s). But it is an accuracy trade, not a tax — thinking **on** scores
  5/6 on real work against 3/6 **off**, so do not set it off globally.
- **Model choice is a trade.** A Coder/Instruct model with no thinking mode is
  the best speed-to-quality default; a reasoning model with thinking on is the
  most capable and ~3-5× slower.
- **Curate tools per task.** 1-2 tools is ~200-470 prompt tokens against ~6,900
  for everything. There is no all-tools mode.
- **Set `cwd` on every `[mcp_servers.*]` entry.** A defensive habit rather than a
  live bug: on squackit < 0.8.1 a mismatched cwd returned `(no results)` for a
  glob that plainly matched — an empty answer, not an error. Fixed since, but the
  habit costs nothing and the failure mode it guards against is the expensive
  kind.

## When capturing test output

Any tool that formats for a terminal self-truncates when captured. `pytest -q`
cuts its summary to the terminal width and assumes 80 columns with no TTY, so a
long test name leaves nothing: a 73-character `FAILED file::test - ` prefix
leaves 7, and the stored message is `'Asse...'`.

**Fixed since blq-cli v1.1.0** (`861b382`), which sets `CAPTURE_COLUMNS = 200` and
`env.setdefault("COLUMNS", "200")` around the capture; duck_hunt#57 is closed too.
On v1.1.0 or later `blq run test` is already wide and needs nothing:

```bash
blq run test                  # v1.1.0+: wide by default
COLUMNS=200 blq run test      # only on blq < 1.1.0 -- a no-op on current versions
```

Check with `blq --version` before reaching for the override. If your messages are
still truncated on a current blq, the override will not help and the cause is
elsewhere — do not let it absorb the search. `--keep-raw` retains the raw log but
does **not** change the parsed message.
