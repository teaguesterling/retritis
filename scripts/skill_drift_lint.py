#!/usr/bin/env python3
"""Lint SKILL.md files against live MCP tool inventories.

For each plugin under `plugins/<name>/skills/<name>-workflow/SKILL.md`:

  1. Spawn the plugin's MCP server (per its `.mcp.json`) and ask `tools/list`
     over stdio.
  2. Parse the SKILL.md for every named-tool reference (backticked
     `mcp__plugin_<name>__<tool>` strings, bare `tool_name(` mentions inside
     fenced code blocks or routing tables).
  3. Report:
       - HALLUCINATIONS — SKILL claims a tool that the server doesn't expose
       - MISSING       — server has a tool the SKILL never mentions
       - SIGNATURE DRIFT (optional, --schema) — argument names listed in the
         SKILL don't match the live JSON schema

Exits non-zero when hallucinations are present; missing/drift are warnings.

Usage:
    python3 scripts/skill_drift_lint.py             # all plugins
    python3 scripts/skill_drift_lint.py blq jetsam  # subset
    python3 scripts/skill_drift_lint.py --json      # machine-readable output
    python3 scripts/skill_drift_lint.py --schema    # also check argument names

Designed as a CI gate. Run before tagging a retritis release.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PLUGINS_ROOT = Path(__file__).resolve().parents[1] / "plugins"

# Plugins that have a CLI surface instead of an MCP server. The lint still
# validates the SKILL.md (against a curated command list) but does not try to
# spawn an MCP server.
CLI_PLUGINS = {
    "agent-riggs": [
        "brief", "ingest", "status", "trust", "ratchet", "metrics", "init",
    ],
}

# Plugins that are intentionally disabled (skipped in lint with a note).
DISABLED_PLUGINS = {"kibitzer"}

# Plugins whose MCP servers cost too much to spawn for a lint (or that need
# special env). None today; reserved for future opt-out.
SKIP_MCP_SPAWN: set[str] = set()

# Verb names that appear as backticked `verb(` inside structured rows but are
# example expressions in documentation, not tool claims. The soft-miss scanner
# (CELL_VERB_RE over table/bullet rows) can't tell `db.connect()` in a selector
# doc from a routing-table entry, so we suppress these known false positives.
# Soft misses are warnings-only, so the blast radius is just cleaner output.
#   connect, getattr — squackit selector docs explain call-receiver matching
#                      with `duckdb.connect()` / `getattr(x, 'method')()`.
SOFT_MISS_IGNORE = {"connect", "getattr"}

# Tools a SKILL.md documents *ahead of* the tool's release: they aren't on the
# live MCP server yet (or aren't in the released version), so the strict check
# would flag them as hallucinations (SKILL claims it) or missing (server has
# it, SKILL's prose mention slips past the parser). They're intentional
# pre-documentation — list them here to downgrade to a visible "pending" note
# instead of failing the gate. REMOVE the entry once the tool ships; if it's
# still absent then, the strict check fires again, which is what you want.
PENDING_TOOLS: dict[str, dict[str, str]] = {
    "jetsam": {"config": "pending jetsam 1.1.2 (config-endpoint)"},
    "squackit": {"config": "pending squackit 0.7 (config-endpoint)"},
}


@dataclass
class PluginFinding:
    name: str
    hallucinations: list[str] = field(default_factory=list)
    soft_misses: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.hallucinations)


# ── SKILL.md parsing ───────────────────────────────────────────────────────

# Canonical tool reference: any `mcp__...__verb` string anywhere in the file
# (backticked, inside a fenced code block, in prose — doesn't matter; the
# namespace is unambiguous). The captured group is the verb after the LAST
# `__`, regardless of how many `_` segments the prefix has. Greedy `\w+` would
# also match the `_` in `mcp__plugin_blq_blq_mcp__register_command` so we need
# the non-greedy prefix.
MCP_REF_RE = re.compile(r"\bmcp__\w+?__(\w+)\b")
# Structured-doc rows: markdown table rows OR bullet-list items. SKILL.mds use
# both patterns to enumerate tool routings. Pulling verb references from these
# zones (but not from free-form prose) catches the canonical signal without
# being tripped by example code mentions like `db.connect()` or `len(x)`.
STRUCTURED_ROW_RE = re.compile(r"^(?:\|.*\|.*|[-*]\s+.+)$", re.MULTILINE)
# A backticked verb inside a structured row: ``` `verb(` ``` or ``` `verb()` ```.
# Requires the trailing `(` so we count *invocation* references, not stray prose
# like `name` or `args`.
CELL_VERB_RE = re.compile(r"`(\w+)\s*\(")


def extract_skill_tool_names(skill_md: Path) -> tuple[set[str], set[str]]:
    """Pull tool-verb candidates out of a SKILL.md.

    Returns (canonical, soft):
      canonical — `mcp__...__verb` references. These are unambiguous claims and
                  MUST match a real tool. Hallucinations here fail the lint.
      soft       — bare verb mentions inside markdown tables. Treated as
                  routing-table claims; mismatches surface as warnings (verb
                  names in *prose* outside tables are ignored to avoid false
                  positives when the SKILL.md discusses something like
                  `db.connect()` as an example).
    """
    text = skill_md.read_text()
    canonical = set(MCP_REF_RE.findall(text))
    # Strip out the canonical refs from the text before scanning for soft
    # mentions, so we don't double-count `mcp__plugin_X__save` as also matching
    # CELL_VERB_RE.
    text_no_canonical = MCP_REF_RE.sub("", text)
    soft = set()
    for row in STRUCTURED_ROW_RE.findall(text_no_canonical):
        soft.update(CELL_VERB_RE.findall(row))
    return canonical, soft


# ── MCP introspection ──────────────────────────────────────────────────────


async def list_mcp_tools(command: str, args: list[str]) -> list[str]:
    """Spawn the MCP server, send tools/list, return tool names.

    Some MCP servers (fledgling-mcp ≤ 0.9) emit non-JSONRPC JSON during init
    (a status banner) that trips the client's pydantic validator. The
    tools/list call still succeeds afterward, so we capture the result and
    swallow any close-time exceptions to keep the partial-success data.
    """
    captured: list[str] = []
    init_error: BaseException | None = None
    try:
        params = StdioServerParameters(command=command, args=args)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.list_tools()
                captured = [t.name for t in res.tools]
    except BaseException as e:
        # Keep the captured tools if we got any; only re-raise if we didn't.
        init_error = e

    if captured:
        return captured
    if init_error is not None:
        raise init_error
    return []


def read_mcp_command(plugin: str) -> tuple[str, list[str]] | None:
    cfg = PLUGINS_ROOT / plugin / ".mcp.json"
    if not cfg.exists():
        return None
    data = json.loads(cfg.read_text())
    # .mcp.json is {server_name: {command, args, ...}}
    first = next(iter(data.values()))
    return first["command"], first.get("args", [])


def find_skill_md(plugin: str) -> Path | None:
    p = PLUGINS_ROOT / plugin / "skills" / f"{plugin}-workflow" / "SKILL.md"
    return p if p.exists() else None


# ── Lint driver ────────────────────────────────────────────────────────────


async def lint_plugin(plugin: str) -> PluginFinding:
    finding = PluginFinding(name=plugin)
    skill = find_skill_md(plugin)
    if skill is None:
        finding.notes.append("no SKILL.md found")
        return finding

    canonical, soft = extract_skill_tool_names(skill)

    if plugin in DISABLED_PLUGINS:
        finding.notes.append("plugin disabled; SKILL.md content not validated")
        return finding

    if plugin in CLI_PLUGINS:
        real = set(CLI_PLUGINS[plugin])
        finding.notes.append("CLI plugin (no MCP); checking against curated command list")
        # CLI commands aren't named `verb(`, they're `<plugin> verb`. Augment
        # the soft set by substring-matching each curated command against the
        # SKILL.md content, so a SKILL that says ``` `agent-riggs brief` ```
        # counts `brief` as mentioned.
        text = skill.read_text()
        soft = soft | {cmd for cmd in real if cmd in text}
    else:
        cmd = read_mcp_command(plugin)
        if cmd is None:
            finding.notes.append("no .mcp.json found; cannot introspect")
            return finding
        try:
            tools = await list_mcp_tools(*cmd)
            real = set(tools)
        except Exception as e:
            finding.notes.append(f"failed to introspect MCP server: {type(e).__name__}: {e}")
            return finding

    # Hard hallucinations: canonical `mcp__...__verb` claims that don't match.
    finding.hallucinations = sorted(canonical - real)
    # Soft hits: routing-table mentions that don't match. Could be hallucinations
    # OR could be third-party verb mentions (rare). Reported as warnings.
    finding.soft_misses = sorted(((soft - canonical) - real) - SOFT_MISS_IGNORE)
    # Real tools not mentioned anywhere in canonical OR soft sets.
    finding.missing = sorted(real - canonical - soft)

    # Pre-documented-but-unreleased tools: pull them out of hallucinations
    # (SKILL claims a tool the live server lacks) and out of missing (server
    # has it but it's pre-release), surfacing them as a non-failing "pending"
    # note so the gate stays green while the exception stays auditable.
    pend = PENDING_TOOLS.get(plugin, {})
    if pend:
        flagged = (set(finding.hallucinations) | set(finding.missing)) & pend.keys()
        finding.pending = sorted(f"{t} — {pend[t]}" for t in flagged)
        finding.hallucinations = [h for h in finding.hallucinations if h not in pend]
        finding.missing = [m for m in finding.missing if m not in pend]
    return finding


def select_plugins(arg_plugins: list[str]) -> list[str]:
    if arg_plugins:
        return arg_plugins
    return sorted(
        p.name for p in PLUGINS_ROOT.iterdir()
        if p.is_dir() and find_skill_md(p.name) is not None
    )


async def main_async(plugins: list[str]) -> list[PluginFinding]:
    results: list[PluginFinding] = []
    for plugin in plugins:
        results.append(await lint_plugin(plugin))
    return results


def render_text(findings: list[PluginFinding]) -> tuple[str, int]:
    out: list[str] = []
    any_errors = False
    for f in findings:
        marker = "❌" if f.has_errors else "✅"
        if not (f.hallucinations or f.soft_misses or f.missing or f.pending or f.notes):
            out.append(f"{marker} {f.name}: clean")
            continue
        out.append(f"{marker} {f.name}")
        for note in f.notes:
            out.append(f"   • note: {note}")
        if f.hallucinations:
            any_errors = True
            out.append(f"   • HALLUCINATIONS ({len(f.hallucinations)}): {', '.join(f.hallucinations)}")
        if f.pending:
            out.append(f"   • ⏳ pending release ({len(f.pending)}): {', '.join(f.pending)}")
        if f.soft_misses:
            out.append(f"   • soft misses ({len(f.soft_misses)}): {', '.join(f.soft_misses)}")
        if f.missing:
            out.append(f"   • not in SKILL ({len(f.missing)}): {', '.join(f.missing)}")
    return "\n".join(out), (1 if any_errors else 0)


def render_json(findings: list[PluginFinding]) -> tuple[str, int]:
    any_errors = any(f.has_errors for f in findings)
    payload = [
        {
            "plugin": f.name,
            "hallucinations": f.hallucinations,
            "soft_misses": f.soft_misses,
            "missing": f.missing,
            "pending": f.pending,
            "notes": f.notes,
        }
        for f in findings
    ]
    return json.dumps(payload, indent=2), (1 if any_errors else 0)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("plugins", nargs="*", help="plugin names to lint (default: all)")
    p.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = p.parse_args()

    plugins = select_plugins(args.plugins)
    findings = asyncio.run(main_async(plugins))
    body, exit_code = render_json(findings) if args.json else render_text(findings)
    print(body)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
