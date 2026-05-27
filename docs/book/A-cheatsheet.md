# Appendix A — The bash → suite cheat sheet

Pin this. The left column is the reflex to suppress; the right is the tool to reach for.

## Find & search
| Instead of | Use |
|---|---|
| `grep -rn "text"` | `squackit.search_code` / `fledgling.SearchCode`; `find_code_ranked` for best matches |
| `grep -rn "def name"` | `squackit.find` / `find_names` / `fledgling.FindDefinitions` |
| find a symbol's callers | `squackit.call_graph`, `squackit.investigate` |
| `grep` in docs | `squackit.search_docs` + `read_doc_section` / `fledgling.SearchDocs` |
| search past sessions/chat | `squackit.search_chat` / `search_messages` / `fledgling.ChatSearch` |
| `ast-grep`-style structural | `squackit.ast_select_from` (pluckit selector) / `squackit.pluck` |

## Read & navigate
| Instead of | Use |
|---|---|
| `cat file` | `squackit.read_source` / `squackit.view` / `fledgling.ViewCode` |
| `sed -n '20,60p'` | `squackit.read_source(range)` / `fledgling.ReadLines` |
| `find . -name "*.py"` | `squackit.list_files` / `fledgling.ExploreProject` |
| "explain this repo" | `squackit.project_overview` / `explore` / `fledgling.ExploreProject` |
| understand one symbol | `squackit.investigate(name)` |

## Diff & history
| Instead of | Use |
|---|---|
| `git status` | `squackit.working_tree_status` / `jetsam.status` |
| `git diff` | `squackit.file_diff`; `squackit.structural_diff` for *what* changed |
| `git log -p file` | `squackit.file_changes` / `recent_changes` / `fledgling.GitShow` |
| review my changes | `fledgling.ReviewChanges` / `squackit.review` |

## Build, test, verify (never pipe)
| Instead of | Use |
|---|---|
| `pytest`/`make`/`npm test` | `blq.run("<cmd>")` (register once with `blq.register_command`) |
| `… | tail -20` | `blq.output(run_id, tail=20)` |
| read failures | `blq.errors` / `blq.status` |
| compare runs | `blq.diff` / `blq.history` |

## Git & PRs (plan → confirm)
| Instead of | Use |
|---|---|
| `git add && git commit` | `jetsam.save` → `jetsam.confirm` |
| `git pull --rebase` / push | `jetsam.sync` → `confirm` |
| open/update a PR | `jetsam.ship` → `confirm`; `jetsam.pr_view` |
| `gh pr list/review` | `jetsam.pr_list` / `pr_review` |
| anything uncovered | `jetsam.git` (last resort) |

## Govern, generate, remember
| Goal | Use |
|---|---|
| check/switch mode | `kibitzer.GetFeedback` / `kibitzer.ChangeToolMode` |
| get help on a tool/error | `kibitzer.GetDocContext`; or each server's `help`/`Help`/`commands`/`language_spec` |
| generate+run a constrained program | `lackpy.generate` → `validate` → `run_program` |
| recall/learn across sessions | `agent-riggs ingest`; promoted ratchets surface via kibitzer |

## When unsure which tool
`squackit.help` · `fledgling.Help` · `blq.commands` · `lackpy.language_spec` · `jetsam.status`
