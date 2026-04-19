# Retritis

*Retritis* (n.): inflammation caused by repeated retries. A chronic condition of agent-assisted development. No known cure — only palliative treatments.

---

## Diagnosis

You have retritis if:

- You've copy-pasted terminal output into a chat window more than twice today
- You've typed `git add . && git commit -m "wip" && git push` from muscle memory while an agent watches
- You've explained the same codebase structure to three different Claude sessions
- You've lost work to a session crash and reconstructed it by hand
- You've written a bash script to avoid writing a bash script

## Treatment

Each tool in the suite addresses a specific symptom. None of them came from a plan. They came from the moment where you think "I've done this enough times."

### Parsing & querying

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [sitting_duck](https://github.com/teague/sitting-duck) | "I need to find all functions matching X across 27 languages" | CSS selectors over tree-sitter ASTs in DuckDB |
| [pluckit](https://github.com/teague/pluckit) | "I want to query, mutate, test, and commit code in one chain" | jQuery for source code. Fluent API over sitting_duck |

### Code intelligence

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [squackit](https://github.com/teague/squackit) | "Claude keeps grepping for definitions and missing half of them" | MCP server + CLI with smart defaults, session caching, compound workflows |
| [fledgling](https://github.com/teague/source-sextant) | "I need cross-file resolution, call graphs, structural similarity" | SQL macros over DuckDB. The query layer underneath squackit |

### History

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [duck_tails](https://github.com/teague/duck-tails) | "Who changed this function and when?" | Git history as queryable DuckDB tables |

### Build & test

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [blq](https://github.com/teague/lq) | "I keep copy-pasting build output into the chat" | Build log capture, sandbox presets, structured query. MCP or CLI |

### Policy

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [umwelt](https://github.com/teague/umwelt) | "Permissions are spread across 5 different systems" | CSS-syntax policy language with Datalog semantics over Beer's VSM |
| [ducklog](https://github.com/teague/ducklog) | "I need to query policy decisions with plain SQL" | Compiles umwelt policy to DuckDB. Authorization as materialized views |

### Git workflow

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [jetsam](https://github.com/teague/jetsam) | "Did I forget to push?" | Save, sync, ship. Preview plans before execution |

### Generation

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [lackpy](https://github.com/teague/lackpy) | "I want a local model that knows my tool APIs" | Micro-inferencer. Qwen 2.5 Coder 3B, local, $0 |

### Observation & learning

| Tool | Symptom | Treatment |
|------|---------|-----------|
| [kibitzer](https://github.com/teague/kibitzer) | "Claude keeps using grep when there's a structured tool for that" | Watches tool calls, suggests alternatives, coaches toward better patterns |
| [agent-riggs](https://github.com/teague/agent-riggs) | "The same effective pattern keeps getting rediscovered across sessions" | Cross-session trace analysis, pattern extraction, template promotion |

### Human-side palliatives

| Tool | Symptom | Treatment |
|------|---------|-----------|
| tmux-use | "Which tmux session was I in?" | Color-coded session management |
| git-wt | "Stash, switch, pop, merge, switch back" | Git worktree wrapper for structured layouts |
| ffs | "Claude crashed mid-task and I lost everything" | Find Failed Sessions. Crash recovery with runbooks |
| init-dev | "Setting up fledgling + blq + jetsam for the 15th time" | Project bootstrapping with auto-detection |

---

## Claude Code Plugins

The quickest way to start treatment. Install the plugin marketplace, then pick your prescriptions.

```bash
# Add the retritis pharmacy
/plugin marketplace add teaguesterling/retritis

# Fill prescriptions individually
/plugin install blq@retritis
/plugin install jetsam@retritis
/plugin install fledgling@retritis
/plugin install squackit@retritis
/plugin install kibitzer@retritis
```

Each plugin bundles:
- **MCP server config** — tool availability
- **Skills** — routing instructions ("instead of grep, use find_definitions")
- **Hooks** (optional) — gentle warnings when you reach for bash instead of the structured tool

See [plugins/](plugins/) for the full formulary.

---

## Prognosis

There is no cure. The condition is progressive — each tool you build reveals new friction, which produces new tools. This is by design. The [ratchet](https://judgementalmonad.com/blog/fuel/index) only turns one direction.

The good news: the symptoms become manageable. A year ago, half the time with Claude was infrastructure. Now it's handled. The freed attention compounds.

The bad news: you will name things like "retritis" and think it's funny.

---

## Further reading

- [judgementalmonad.com](https://judgementalmonad.com) — The blog series behind the suite
- [Ratchet Fuel](https://judgementalmonad.com/blog/fuel/index) — The agent-side ratchet
- [The Tools That Built Themselves](https://judgementalmonad.com/blog/tools/the-tools-that-built-themselves) — How and why these tools exist
- [The Ma of Multi-Agent Systems](https://judgementalmonad.com/blog/ma/index) — The theory underneath
