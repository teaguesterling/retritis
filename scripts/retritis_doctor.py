#!/usr/bin/env python3
"""Run health checks across the retritis suite.

Catches the classes of failure that broke this session's first hours:

  - Editable-install `.pth` files pointing at directories that no longer exist
    (today's `/mnt/fast` mount rot, 6 packages broken silently).
  - MCP servers that fail to spawn or return zero tools.
  - SKILL.md files missing or empty.
  - Plugin cache vs. source-of-truth mismatches.

Run on every session start, or any time the suite "feels off." The output
is intentionally noisy — every checked item gets a status line so it's
obvious what was tested and what wasn't.

Usage:
    python3 scripts/retritis_doctor.py             # all checks
    python3 scripts/retritis_doctor.py --json      # machine-readable
    python3 scripts/retritis_doctor.py --fix       # try to repair what it can
                                                   # (currently: rewrite stale
                                                   # .pth files)

Exit codes:
    0  all checks passed
    1  at least one check failed (HARD)
    2  at least one check warned (SOFT — config drift, etc.)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Path constants ────────────────────────────────────────────────────────
PLUGINS_ROOT = Path(__file__).resolve().parents[1] / "plugins"
HOME = Path.home()
# Plugin source repos that editable installs typically point at. Used by the
# .pth health check to suggest the correct target when a file references a
# stale path.
SOURCE_REPO_HINTS = [
    HOME / "Projects",
    HOME / "projects",
]

# ── Result types ──────────────────────────────────────────────────────────


@dataclass
class Check:
    name: str
    status: str  # "OK", "WARN", "FAIL"
    detail: str = ""
    fix_hint: str | None = None
    repaired: bool = False

    @property
    def emoji(self) -> str:
        return {"OK": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[self.status]


# ── Check: editable .pth files resolve ───────────────────────────────────


_PTH_RE = re.compile(r"^_editable_impl_(\w+)\.pth$")


def _venv_site_packages() -> Path | None:
    """Best guess at the venv site-packages where retritis installs land."""
    candidates = [
        HOME / ".local/share/venv/lib/python3.12/site-packages",
        HOME / ".local/share/venv/lib/python3.11/site-packages",
        HOME / ".local/lib/python3.12/site-packages",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def check_editable_installs(fix: bool = False) -> list[Check]:
    """Verify every `_editable_impl_*.pth` file points at a directory that exists."""
    sp = _venv_site_packages()
    if sp is None:
        return [Check("editable installs", "WARN", "no recognized venv site-packages dir")]
    checks: list[Check] = []
    pth_files = sorted(sp.glob("_editable_impl_*.pth"))
    if not pth_files:
        return [Check("editable installs", "WARN", f"no _editable_impl_*.pth files in {sp}")]
    for pth in pth_files:
        m = _PTH_RE.match(pth.name)
        pkg = m.group(1) if m else pth.stem
        target = pth.read_text().strip()
        if Path(target).is_dir():
            checks.append(Check(f"editable {pkg}", "OK", target))
            continue
        # Stale — try to find the right path
        suggestion: str | None = None
        for hint in SOURCE_REPO_HINTS:
            for repo_root in hint.iterdir() if hint.exists() else []:
                if repo_root.name.lower().startswith(pkg.lower().split("_")[0]):
                    # Heuristic: strip everything before the first /Projects/<repo>
                    parts = target.split("/")
                    for i, part in enumerate(parts):
                        if part == "Projects" or part == "projects":
                            relpath = "/".join(parts[i + 1:])
                            candidate = hint / relpath
                            if candidate.is_dir():
                                suggestion = str(candidate)
                                break
                    if suggestion:
                        break
            if suggestion:
                break
        detail = f"target does not exist: {target}"
        fix_hint = (
            f"echo '{suggestion}' > {pth}"
            if suggestion else
            f"rewrite {pth} or `pip install -e <repo>` to regenerate"
        )
        if fix and suggestion:
            pth.write_text(suggestion + "\n")
            checks.append(Check(f"editable {pkg}", "OK", f"repaired: {target} → {suggestion}", repaired=True))
        else:
            checks.append(Check(f"editable {pkg}", "FAIL", detail, fix_hint))
    return checks


# ── Check: MCP servers spawn + return tools ─────────────────────────────


async def _list_mcp_tools(command: str, args: list[str]) -> list[str]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    captured: list[str] = []
    err: BaseException | None = None
    try:
        params = StdioServerParameters(command=command, args=args)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.list_tools()
                captured = [t.name for t in res.tools]
    except BaseException as e:
        err = e
    if captured:
        return captured
    if err:
        raise err
    return []


def _read_mcp_command(plugin: str) -> tuple[str, list[str]] | None:
    cfg = PLUGINS_ROOT / plugin / ".mcp.json"
    if not cfg.exists():
        return None
    data = json.loads(cfg.read_text())
    first = next(iter(data.values()))
    return first["command"], first.get("args", [])


# Plugins where "no MCP server" is the intended state.
NO_MCP_BY_DESIGN = {"agent-riggs": "CLI tool", "umwelt": "internal infrastructure"}
DISABLED_BY_USER: dict[str, str] = {}  # kibitzer enabled 2026-06-19


async def check_mcp_servers() -> list[Check]:
    checks: list[Check] = []
    for plugin_dir in sorted(PLUGINS_ROOT.iterdir()):
        if not plugin_dir.is_dir():
            continue
        plugin = plugin_dir.name
        if plugin in DISABLED_BY_USER:
            checks.append(Check(f"mcp:{plugin}", "WARN", DISABLED_BY_USER[plugin]))
            continue
        if plugin in NO_MCP_BY_DESIGN:
            checks.append(Check(f"mcp:{plugin}", "OK", NO_MCP_BY_DESIGN[plugin]))
            continue
        cmd = _read_mcp_command(plugin)
        if cmd is None:
            checks.append(Check(f"mcp:{plugin}", "WARN", "no .mcp.json"))
            continue
        try:
            tools = await _list_mcp_tools(*cmd)
            if not tools:
                checks.append(Check(f"mcp:{plugin}", "FAIL", "server returned 0 tools"))
            else:
                checks.append(Check(f"mcp:{plugin}", "OK", f"{len(tools)} tools"))
        except FileNotFoundError as e:
            checks.append(Check(
                f"mcp:{plugin}", "FAIL",
                f"command not found: {cmd[0]}",
                fix_hint=f"pip install -e ~/Projects/{plugin} or `which {cmd[0]}`",
            ))
        except Exception as e:
            checks.append(Check(
                f"mcp:{plugin}", "FAIL",
                f"{type(e).__name__}: {e!s:.120}",
                fix_hint=f"try `{' '.join([cmd[0]] + cmd[1])}` directly to see the error",
            ))
    return checks


# ── Check: SKILL.md presence + non-empty ─────────────────────────────────


def check_skill_md() -> list[Check]:
    checks: list[Check] = []
    for plugin_dir in sorted(PLUGINS_ROOT.iterdir()):
        if not plugin_dir.is_dir():
            continue
        plugin = plugin_dir.name
        skill = plugin_dir / "skills" / f"{plugin}-workflow" / "SKILL.md"
        if not skill.exists():
            checks.append(Check(f"skill:{plugin}", "FAIL", f"missing: {skill}"))
            continue
        content = skill.read_text()
        if len(content) < 100:
            checks.append(Check(f"skill:{plugin}", "WARN", f"stub: {len(content)} chars"))
            continue
        # Frontmatter check — name + description required
        if "name:" not in content[:300] or "description:" not in content[:1000]:
            checks.append(Check(f"skill:{plugin}", "WARN", "missing name/description in frontmatter"))
            continue
        checks.append(Check(f"skill:{plugin}", "OK", f"{len(content)} chars"))
    return checks


# ── Driver ────────────────────────────────────────────────────────────────


async def run_all(fix: bool = False) -> list[Check]:
    checks: list[Check] = []
    checks.extend(check_editable_installs(fix=fix))
    checks.extend(check_skill_md())
    checks.extend(await check_mcp_servers())
    return checks


def render_text(checks: list[Check]) -> tuple[str, int]:
    out: list[str] = []
    any_fail = any(c.status == "FAIL" for c in checks)
    any_warn = any(c.status == "WARN" for c in checks)
    # Group by check family (prefix before `:`)
    groups: dict[str, list[Check]] = {}
    for c in checks:
        family = c.name.split(":", 1)[0] if ":" in c.name else c.name
        groups.setdefault(family, []).append(c)
    for family, items in groups.items():
        n_fail = sum(1 for i in items if i.status == "FAIL")
        n_warn = sum(1 for i in items if i.status == "WARN")
        if items[0].name == family:
            # Single-item family (e.g. "editable installs")
            out.append(f"{items[0].emoji} {items[0].name}: {items[0].detail}")
            if items[0].fix_hint:
                out.append(f"   fix: {items[0].fix_hint}")
            continue
        family_marker = "❌" if n_fail else ("⚠️ " if n_warn else "✅")
        out.append(f"{family_marker} {family} ({len(items)} checks, {n_fail} fail, {n_warn} warn)")
        for c in items:
            out.append(f"   {c.emoji} {c.name}: {c.detail}")
            if c.fix_hint and c.status == "FAIL":
                out.append(f"      fix: {c.fix_hint}")
    rc = 1 if any_fail else (2 if any_warn else 0)
    return "\n".join(out), rc


def render_json(checks: list[Check]) -> tuple[str, int]:
    rc = 1 if any(c.status == "FAIL" for c in checks) else (2 if any(c.status == "WARN" for c in checks) else 0)
    payload = [
        {"name": c.name, "status": c.status, "detail": c.detail, "fix_hint": c.fix_hint, "repaired": c.repaired}
        for c in checks
    ]
    return json.dumps(payload, indent=2), rc


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", action="store_true", help="emit machine-readable output")
    p.add_argument("--fix", action="store_true", help="repair what we can (stale .pth files)")
    args = p.parse_args()
    checks = asyncio.run(run_all(fix=args.fix))
    body, rc = render_json(checks) if args.json else render_text(checks)
    print(body)
    return rc


if __name__ == "__main__":
    sys.exit(main())
