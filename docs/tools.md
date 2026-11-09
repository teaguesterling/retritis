# Tools

Every tool in the suite, in four groups. Each tool has its own documentation;
this page links to it. Version numbers are left out on purpose: see each
tool's own page for the current release.

## Code intelligence

| Tool | What it does for you | Install | Docs |
|---|---|---|---|
| fledgling | SQL macros over DuckDB: find definitions, callers and code structure, and read git history, docs and past chat sessions. | `pip install fledgling-mcp` | [docs](https://teaguesterling.github.io/fledgling/) |
| squackit | The MCP server and CLI that most users talk to. It wraps fledgling and pluckit with ranked search and session caching. | `pip install squackit` | [docs](https://squackit.readthedocs.io) |
| pluckit | "jQuery for source code": select, view and change code with CSS selectors over the syntax tree. | `pip install ast-pluckit` | [docs](https://pluckit.readthedocs.io) |
| duckeye | A terminal reader for documents, code and data files, with section and selector queries. | `curl -fsSL https://raw.githubusercontent.com/teaguesterling/duckeye/main/install.sh \| bash` | [docs](https://duckeye.readthedocs.io) |

## Workflow

| Tool | What it does for you | Install | Docs |
|---|---|---|---|
| blq | Runs builds and tests, keeps the output, and lets you query the errors later without a re-run. | `pip install "blq-cli[mcp]"` | [docs](https://blq-cli.readthedocs.io) |
| jetsam | Git save, sync and ship as single steps. Each step shows a plan that you confirm first. | `pip install jetsam-mcp` | [docs](https://jetsam-mcp.readthedocs.io) |
| kibitzer | Watches the agent's tool calls, protects paths by mode, and suggests a structured tool in place of the shell. | `pip install kibitzer` | [docs](https://kibitzer.readthedocs.io) |

## Generation, memory and policy

| Tool | What it does for you | Install | Docs |
|---|---|---|---|
| lackpy | Turns a plain-language request into a small, checked program and runs it with a local model. | `pip install "lackpy[mcp]"` | [docs](https://lackpy.readthedocs.io) |
| agent-riggs | Memory across sessions: start-of-session briefings, recurring patterns, trust scores. | `pip install agent-riggs` | [docs](https://agent-riggs.readthedocs.io) |
| umwelt | Agent permission policy written like CSS, compiled to SQLite. Other tools ask it what is allowed. | `pip install "umwelt @ git+https://github.com/teaguesterling/umwelt"` | [docs](https://umwelt.readthedocs.io) |
| nsjail-python | A Python wrapper for Google's nsjail sandbox. | `pip install "nsjail-python[binary]"` | [docs](https://nsjail-python.readthedocs.io) |

`pip install umwelt` installs a different project with the same name. Use the
GitHub URL above.

## DuckDB extensions

These are the foundation the Python tools stand on. Install them from inside
DuckDB.

| Extension | What it does for you | Install | Docs |
|---|---|---|---|
| sitting_duck | Query source-code syntax trees with SQL and CSS selectors, in 27 languages. | `INSTALL sitting_duck FROM community;` | [docs](https://sitting-duck.readthedocs.io) |
| duck_tails | Git history, and files at any revision, as tables. | `INSTALL duck_tails FROM community;` | [docs](https://duck-tails.readthedocs.io) |
| duck_hunt | Parses test, build and CI logs from more than 100 tools into rows. | `INSTALL duck_hunt FROM community;` | [docs](https://duck-hunt.readthedocs.io) |

To install everything at once, follow [Install](install).
