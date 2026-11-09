# Install

These steps follow the suite's install test, which runs in CI on Linux x86-64
(`ubuntu-latest`). That is the tested path. On macOS and other platforms, the
Python steps are the same, but nothing here is tested there.

You need Python 3.10 or later, and Claude Code (or another MCP client).

## 1. Install the Python packages

`retritis` is a metapackage: it pins a set of tool versions that CI has
installed and started together. It is not on PyPI, so install it from GitHub:

```bash
pip install "retritis[all] @ git+https://github.com/teaguesterling/retritis"
```

`[all]` adds the optional tools: lackpy (needs a local
[Ollama](https://ollama.com) model), kibitzer and agent-riggs. To install only the
core servers (squackit, fledgling, pluckit, jetsam, blq), leave out `[all]`.

## 2. Install the DuckDB CLI

`fledgling-mcp serve` runs the `duckdb` command-line program, so it must be on
your `PATH`. CI uses DuckDB 1.5.6. On Linux x86-64:

```bash
curl -fsSL -o duckdb_cli.zip \
  https://github.com/duckdb/duckdb/releases/download/v1.5.6/duckdb_cli-linux-amd64.zip
unzip -o duckdb_cli.zip
install -m 755 duckdb ~/.local/bin/duckdb
duckdb --version
```

On other platforms, see [DuckDB's install page](https://duckdb.org/docs/installation/).

## 3. Install the DuckDB extensions

The servers load these extensions when they start. Install them once, for the
CLI and for the Python `duckdb` module:

```bash
for ext in duckdb_mcp read_lines sitting_duck markdown duck_tails duck_hunt; do
  duckdb -c "INSTALL $ext FROM community"
done
duckdb -c "INSTALL fts"

python -c "
import duckdb
con = duckdb.connect()
for ext in ('sitting_duck', 'duck_tails', 'duck_hunt'):
    con.execute(f'INSTALL {ext} FROM community')
"
```

## 4. Add the plugins to Claude Code

Inside Claude Code:

```text
/plugin marketplace add teaguesterling/retritis
/plugin install fledgling@retritis
/plugin install squackit@retritis
/plugin install blq@retritis
/plugin install jetsam@retritis
/plugin install kibitzer@retritis
/plugin install lackpy@retritis
/plugin install agent-riggs@retritis
/plugin install umwelt@retritis
/plugin install duckeye@retritis
/plugin install test-failure-investigator@retritis
```

The first seven plugins use the tools from step 1. The last three need
something else:

| Plugin | What it needs | Covered by the install test? |
|---|---|---|
| umwelt | `pip install "umwelt @ git+https://github.com/teaguesterling/umwelt"`. Do not run `pip install umwelt`: that name on PyPI is a different project. | No |
| duckeye | `curl -fsSL https://raw.githubusercontent.com/teaguesterling/duckeye/main/install.sh \| bash` | No |
| test-failure-investigator | Nothing. It is a skill that uses the other plugins. | Not applicable |

## 5. Set up each project

In each repository where you want the suite:

```bash
blq init --no-mcp                       # create blq's log store (.bird/) here
blq commands register test "pytest"     # tell blq how this project runs its tests
```

Change `pytest` to the project's own test command. `--no-mcp` stops blq from
writing its own `.mcp.json`, because the plugin already starts the blq server.
The fledgling server needs no setup step: it starts in any repository.

## Next

Read the [field guide](book/index). Its preface is written for the agent: it
gets an agent productive in one session.
