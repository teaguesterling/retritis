# Preface — Getting Your Agent Up and Running

You are an agent. You have landed in a repository that has the **retritis** suite
installed, which means a set of Model Context Protocol (MCP) servers are connected to
your session. This preface is your onboarding. By the end of it you will reach for the
right tool by reflex instead of shelling out to `bash` — and you will be faster, more
accurate, and observable while doing it.

Read this once. It is the highest-leverage thing in the book for you.

## The one idea

> **The codebase is already a database. Query it. Don't re-derive it with a shell.**

When you run `grep -rn "def connect" .`, you are launching a process that walks the file
tree, reads bytes, and pattern-matches lines — throwing away the fact that the project is
*structured*: it has an abstract syntax tree, a git history, a full-text index, and a
chat/session log, all of which the suite has already parsed into a DuckDB database you can
query in milliseconds. `grep` finds the *string* `def connect`. `squackit.find_names` finds
the *definition named* `connect`, tells you its file and line, its signature, who calls it,
and how complex it is — typed, ranked, and without re-reading the tree.

Every time you reach for `bash` to inspect, search, read, run, or commit, ask: *is there a
tool that already knows the answer as data?* Almost always, yes.

## Why tools beat `bash` here (it is not dogma)

| | `bash` (`grep`/`find`/`cat`/`sed`/`git`) | retritis tools |
|---|---|---|
| **Structure** | byte/line matching; no notion of a function, class, or call | AST-aware: definitions, calls, complexity, structural diffs |
| **Speed at scale** | re-walks + re-reads the tree every call | one persistent DuckDB index; cache-hit queries in tens of ms |
| **Ranking** | match order is filesystem order | relevance-ranked (`find_code_ranked`, BM25 FTS) |
| **Composability** | text piped between fragile one-liners | typed results you can pass between tools |
| **Observability** | output vanishes into your transcript | runs/queries are recorded, queryable, and replayable (`blq`) |
| **Policy** | unconstrained; easy to do the wrong thing in the wrong mode | mode- and policy-aware (`kibitzer`, `umwelt`) — guardrails, not surprises |
| **Determinism** | depends on the host's `grep`/`sed`/locale | one engine, one semantics, everywhere |

`bash` is still the right tool for genuinely unstructured, one-off shell work. But for
*understanding code, running builds, and moving through git*, the suite is strictly better
and the suite is watching — so using it also makes you legible to the tools that coach and
remember.

## The reflex table — stop reaching for these, reach for those

| When you would type… | Reach for… |
|---|---|
| `grep -rn "foo"` | `squackit.search_code` / `fledgling.SearchCode` (text+AST), or `squackit.find_names` for symbols |
| `grep -rn "def foo"` / find a definition | `squackit.find` / `fledgling.FindDefinitions` / `squackit.find_names` |
| "where is this used / who calls it" | `squackit.call_graph`, `squackit.investigate` (symbol dossier) |
| `cat file.py` / `sed -n '20,60p'` | `squackit.read_source` / `fledgling.ReadLines` / `squackit.view` |
| `find . -name "*.py"` | `squackit.list_files` / `fledgling.ExploreProject` |
| `grep` across docs / READMEs | `squackit.search_docs` / `fledgling.SearchDocs` (+ `read_doc_section`) |
| "what changed" / `git diff` | `squackit.working_tree_status`, `squackit.file_diff`, `squackit.structural_diff`, `fledgling.ReviewChanges` |
| `git log -p file` / history | `squackit.file_changes` / `squackit.recent_changes` / `fledgling.GitShow` |
| `pytest … | tail -20` | `blq.run("test")` then `blq.output(run_id, tail=20)` / `blq.errors` — **never pipe** |
| build/lint/typecheck + read output | `blq.run(<cmd>)` + `blq.status` / `blq.errors` / `blq.output` |
| `git add -A && git commit -m …` | `jetsam.save` → `jetsam.confirm` |
| `git pull --rebase` / push | `jetsam.sync` → `jetsam.confirm`; `jetsam.ship` for a PR |
| `gh pr view/list/review` | `jetsam.pr_view` / `pr_list` / `pr_review` |
| "search my past sessions / chats" | `squackit.search_chat` / `search_messages` / `fledgling.ChatSearch` |
| "explain this project to me" | `squackit.project_overview` / `squackit.explore` / `fledgling.ExploreProject` |
| "I don't know which tool" | `squackit.help`, `fledgling.Help`, `blq.commands`, `lackpy.language_spec` |

> **Agent Recipe — orienting in an unfamiliar repo**
> 1. `squackit.project_overview` (or `fledgling.ExploreProject`) — shape, languages, entry points.
> 2. `squackit.search_docs("architecture")` + `read_doc_section` — the human's own map.
> 3. `squackit.find` / `investigate` on the symbols the task names — go straight to the code.
> You now know the project without having `cat`-ed a single file.

## First-session setup (do this once, in order)

1. **Confirm the servers are connected.** You should see MCP tools namespaced
   `squackit`, `fledgling`, `blq`, `jetsam`, `kibitzer`, `lackpy`. If a family is missing,
   that capability is simply unavailable — fall back gracefully, don't fail loudly.

2. **Warm the index.** squackit/fledgling answer from a DuckDB index built over the AST +
   FTS. The first `search_code`/`FindCode` builds it (a few seconds); after that, queries
   are cache hits. If the project supports the **persistent cache** (fledgling ≥ 0.11),
   the index is file-backed and survives across sessions — the first query of the day
   pays the build, the rest are ~tens of ms. (See Chapter 3.)

3. **Check your mode.** kibitzer runs you in a *mode* (`free`, `implement`, `test`,
   `docs`, `explore`, `review`) that governs which paths are writable and how it coaches.
   `kibitzer.GetFeedback` shows your current mode and any intercepted patterns;
   `kibitzer.ChangeToolMode` switches. If an edit is unexpectedly refused, you are probably
   in a mode that doesn't permit writes there — switch deliberately rather than working
   around it. (See Chapter 8.)

4. **Register your build commands once.** Tell `blq` how to run the project's tests/build
   (`blq.register_command`), then always run them through `blq.run` so the output is
   captured and queryable instead of scrolling past in your transcript.

## The loop you are actually running

Everything in the suite serves one cycle. Name it to yourself; it keeps you tool-first:

```
        observe ───────────► act ───────────► verify ───────────► learn
   squackit / fledgling    (edit files)      blq (run+query)    kibitzer / agent-riggs
   "what is true now?"     "change it"        "did it work?"     "remember/coach for next time"
                                  ▲                                      │
                                  └──────────── jetsam (save/ship) ◄─────┘
```

- **Observe** with squackit/fledgling — never guess the code; query it.
- **Act** by editing files (this is the one step that is genuinely yours, not a tool).
- **Verify** with blq — run the tests/build *through the tool* and read the captured
  errors; don't pipe and don't trust a green you didn't capture.
- **Learn**: kibitzer coaches in-session; agent-riggs remembers across sessions (a failure
  pattern seen once can be surfaced as a fix next time).
- **Persist** the change with jetsam, which turns the git dance into a confirmable plan.

## How the pieces relate (the map)

```
            ┌──────────────────────────── observe ────────────────────────────┐
            │   squackit  (the agent's code-intelligence server)               │
            │      └─ built on ─ pluckit (CSS-over-AST) + fledgling (SQL/DuckDB)│
            └──────────────────────────────────────────────────────────────────┘
   verify   blq (build-log query)          persist   jetsam (git workflow)
   coach    kibitzer (modes + hooks) ◄── policy ── umwelt (CSS-like cascade)
   generate lackpy (intent→program, local models, restricted exec ── nsjail)
   remember agent-riggs (turns, trust, ratchets) ──► kibitzer surfaces promoted fixes
```

Read it as: **fledgling** is the engine (SQL macros over a DuckDB-parsed AST + FTS);
**pluckit** is a CSS-like selector language over that AST; **squackit** composes both into
the high-level tools you actually call. **blq** and **jetsam** cover verify and persist.
**kibitzer** governs and coaches you, reading policy compiled by **umwelt**. **lackpy**
generates and safely runs programs (sandboxed by **nsjail**), and **agent-riggs** closes
the loop by learning across sessions. The rest of the book takes them one at a time.

## Three habits that make you good at this

1. **Query before you read.** Don't open a file to find something — find it with a tool,
   then read exactly the lines it points to (`read_source`/`ReadLines` with a range).
2. **Capture before you trust.** Run builds/tests through `blq` and read `blq.errors`.
   A test result you piped to `tail` and eyeballed is not a result you can act on later.
3. **Stay legible.** Use the tools even when `bash` would work, because kibitzer and
   agent-riggs can only coach and remember what they can see. Your future self (next
   session) inherits what this session made observable.

Now turn to Chapter 1 for the lay of the land, or jump straight to the tool you need.
