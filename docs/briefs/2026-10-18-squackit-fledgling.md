# Brief: make squackit and fledgling reachable

**Status:** both issues were misdiagnosed and have been corrected. Read the
corrected bodies, not the originals. No design pass needed; this is
investigation plus one bug.
**Issues:** teaguesterling/retritis#10 (squackit), #11 (fledgling), #16
(lackpy, related), #18 (the adoption data)
**Origin:** Teague, 2026-10-18. Measurements in
claude.ai/code/session_01XoHU19qnngy1CJnXyX1csz

---

## The prompt

Two MCP servers in this marketplace have **zero recorded invocations across
1,913 sessions** on two machines. Neither zero is a verdict on the tool. Find
out why each is unreachable and fix what can be fixed.

They are two different problems. Do not assume one cause.

## squackit: the server works. The connection does not.

Measured today. Probed by hand with a valid JSON-RPC `initialize`:

```
$ printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}' \
    | squackit mcp serve
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05",
 "capabilities":{...},"serverInfo":{"name":"squackit","version":"3.4.7"}}}
```

It starts, speaks the protocol, and advertises tools, resources and prompts.
The banner goes to stderr, which is correct, and stdout carries only JSON-RPC.

**So the question is why the harness reports `CONNECTION_CLOSED` for a server
that works when run by hand.** That is an investigation, not a fix. Candidates
nobody has checked:

  - the environment the harness launches it under, which differs from an
    interactive shell
  - a startup time limit, if squackit is slow to first byte
  - `--root` or `--profile` defaulting to something unusable in that context
  - the working directory the harness uses

**Do not trust the original issue #10.** It claimed `squackit mcp serve` did
not exist and blamed a version skew. Both were wrong. `mcp serve` is defined at
`squackit/cli.py:31` (the group) and `:36-50` (the command); the "no
subcommands" reading came from piping `--help` through `head -6`, which cut the
`Commands:` section off below the options.

One real but separate oddity: `squackit --version` reports `0.9.0`, from
`pyproject.toml`, while the running server advertises `3.4.7`. Two version
numbers for one program. Worth settling, not the cause of anything here.

## fledgling: genuinely broken, and its own source says why

Stdout is **empty** for a valid `initialize`. Not malformed. Empty. The error
reaches stderr only:

```
Binder Error: Column "timestamp" in REPLACE list not found in FROM clause
```

The cause is documented in a comment above the failing SQL,
`sql/conversations.sql:17-19`:

> including `timestamp`, the whole glob infers 3 (json, filename,
> _source_file) and `timestamp` is simply gone -- so every macro below fails
> to bind, and the first symptom is an unhelpful "Column timestamp in REPLACE
> list not found in ..."

So this is **schema inference over a JSON glob**, not a stray `REPLACE` list.
The glob infers three columns, `timestamp` is not among them, and every macro
built on that relation fails to bind.

Start at `sql/conversations.sql` and whatever reads the transcript glob. The
fix is to make the inferred schema carry `timestamp`: name the columns
explicitly, or read with a declared schema rather than inferring across a glob
whose members differ.

Secondary: the process exits 0 while failing. A non-zero exit would have
surfaced this months ago instead of leaving a silent close.

## A convention that has caught three tools, and may be relevant to squackit

`pip` here installs into `~/.local/share/venv` (Python 3.12), while `python3`
is miniconda's 3.14. Scripts therefore land where PATH does not look, and each
tool reaches PATH by a per-tool symlink:

```
pip       ~/.local/bin/pip      -> ~/.local/share/venv/bin/pip
jetsam    ~/.local/bin/jetsam   -> ~/.local/share/venv/bin/jetsam
blq       ~/.local/bin/blq      -> ~/.local/share/venv/bin/blq
```

`cofctl` was unreachable for exactly this reason and was fixed today by adding
the link. `lackpy` is the same (#16): installed in the venv, three scripts, no
links. **Check whether squackit's failure is environmental in the same family**
before looking for a bug in squackit itself.

Nothing automates these links. Three tools have now been found unreachable for
one reason, so the gap is a convention with no owner rather than three
oversights. Worth proposing a fix for that too.

## Limits

  - **Do not edit `~/.claude` config or permission settings.** If something
    needs a settings change, say so and let Teague decide.
  - **Do not close #10 as invalid.** The server working is a finding; the
    connection failing is still unexplained and still real.
  - Measure before concluding. Every original diagnosis in #10, #11 and #16
    was wrong, and each was wrong because a convenient check stood in for the
    real one.

## First thing to settle

For squackit: reproduce the `CONNECTION_CLOSED` deliberately, under the
harness rather than by hand. Until it reproduces, there is nothing to fix and
any change is a guess.
