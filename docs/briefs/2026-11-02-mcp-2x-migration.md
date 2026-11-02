# Brief: migrate kibitzer and lackpy from FastMCP to MCPServer (mcp 2.x)

**Status:** plan, not started. The stopgap cap is in review as kibitzer#7,
lackpy#68 and retritis#21.
**Origin:** Teague, 2026-11-02: "Pin mcp<2, update release, but then plan to
migrate right after. Pinning is just a stopgap." Reasoning in
claude.ai/code/session_01G4hzdTdzDmuh1Mdmb53wm6

---

## Sitrep (STAR)

**Situation.** The `mcp` Python package released 2.x. It renamed the `FastMCP`
class to `MCPServer` and deleted the `mcp.server.fastmcp` module. Two of our
MCP servers import that module directly. Neither declared an upper version
bound, so 2.x arrived with no commit on our side.

**Task.** Keep the fleet installable today, then move both servers onto the
2.x API before mcp 1.x stops getting fixes.

**Action.** Today: cap `mcp` at `>=1.0,<2` in kibitzer, in lackpy's `mcp`
extra, and in the retritis quality workflow. Next: change the two imports,
check the two behaviour changes listed below, and remove the caps.

**Result.** The cap is measured to restore the boot. One venv, one variable:
`kibitzer mcp serve` exits 0 under mcp 1.30.0 and exits 1 under mcp 2.3.0. The
cap does not reach retritis `fresh-install` until kibitzer 0.9.1 and lackpy
0.16.1 are published, because that job installs from PyPI.

## Structured fields

| Field | Value |
|---|---|
| **Repos** | `kibitzer`, `lackpy`; `retritis` as the suite that caught it |
| **Lands as** | two import changes, then three cap removals |
| **Relates to** | kibitzer#7, lackpy#68, retritis#21 (the caps) |
| **Affects** | `kibitzer mcp serve`, `lackpyctl mcp serve`, retritis `fresh-install` and `quality` |
| **Status** | plan only; no migration code written |
| **Carried forward** | retritis `fresh-install` also fails for two unrelated reasons: squackit's `con.con` AttributeError, and fledgling-mcp finding no duckdb CLI |

## What the rename actually costs

Measured 2026-11-02 by reading both installed packages, not the release notes.
`inspect.signature` on mcp 1.30.0 `FastMCP` and mcp 2.3.0 `MCPServer`:

| Member | 1.30.0 vs 2.3.0 |
|---|---|
| `tool` | identical |
| `resource` | 2.x adds `security: ResourceSecurity \| None = None` |
| `prompt` | identical |
| `add_tool` | identical |
| `run_stdio_async` | identical |
| `run` | 1.x takes `mount_path`; 2.x takes `**kwargs` |

So the decorator surface both servers use is unchanged. The migration is close
to a rename, and the risk is NOT the rename.

## The two behaviour changes that are the real work

1. **`MCPServer` defaults to rejecting some resource URIs.** Its constructor
   defaults `resource_security` to
   `ResourceSecurity(reject_path_traversal=True, reject_absolute_paths=True,
   reject_null_bytes=True)`. `FastMCP` had no such parameter. Any resource that
   accepts an absolute path will be refused where it used to work. Check
   kibitzer's doc-context lookup and every lackpy resource before assuming a
   clean rename.

2. **`run(mount_path=...)` is no longer a named parameter.** It now falls into
   `**kwargs`, so a caller that passes it gets no error and no effect. Grep
   both servers for `mount_path` before changing the import.

## Steps

1. **Measure the current surface.** In a throwaway venv with mcp 2.3.0, import
   each server module and record the exact failure. Do not start from this
   brief's table; re-run `inspect.signature`, because 2.x is young and moving.
2. **kibitzer first.** It has 4 `mcp.` call sites against lackpy's 16, so it
   is the cheaper place to find a surprise. Change
   `from mcp.server.fastmcp import FastMCP` to
   `from mcp.server.mcpserver import MCPServer` in
   `src/kibitzer/mcp/server.py` and rename the constructor call.
3. **Verify with the control retritis uses, not with a unit test.**
   `timeout 15 <venv>/bin/kibitzer mcp serve </dev/null`; success is exit 0 or
   124. Then call `tools/list` and compare the tool names and schemas against
   the 1.x output, so an empty server cannot pass as a working one.
4. **lackpy second**, same two changes in `src/lackpy/mcp/server.py`, same
   control with `lackpyctl mcp serve`, plus a `tools/list` comparison.
5. **Widen the caps last.** Change `>=1.0,<2` to `>=2` in both projects and in
   `retritis/.github/workflows/quality.yml`, in ONE commit per repo, so a
   revert is a single revert.
6. **Release both**, because retritis `fresh-install` installs from PyPI and
   will not see the migration until it is published.

## What would prove this plan wrong

If `tools/list` under 2.x returns a different schema for any tool, the rename
is not a rename and this becomes an interface change with its own brief. If
either server passes an absolute path as a resource URI, step 1 is a redesign
of that resource, not an import swap.
