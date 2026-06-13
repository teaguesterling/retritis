#!/usr/bin/env python3
"""Analyze Skill-invocation rates across Claude Code transcripts.

The premise: a skill is doing its job when sessions invoke it via the Skill
tool BEFORE reaching for the underlying MCP tool family. When sessions only
ever call `mcp__plugin_X__verb` and never `Skill(X-workflow)`, the skill is
loaded but its routing table never reaches the model.

The bypass signal is measured against *routed* MCP calls — explicit
passthrough/escape-hatch verbs (e.g. jetsam's `git` proxy for cross-repo
`git -C`) are excluded, since using them is not a routing failure. And the
hard signal keys on skill_calls == 0 (the skill umbrella never reaching the
model), not on a ratio floor: a plugin whose skill *does* fire isn't BYPASSED
just because one Skill load covers a high volume of downstream tool calls.

This script ingests one or more transcript JSONL files, counts tool calls
per family, and reports the Skill:MCP ratio per plugin. A persistently low
ratio is a signal that the skill's description doesn't match user phrasing.

Usage:
    python3 scripts/trigger_analysis.py TRANSCRIPT [TRANSCRIPT...]
    python3 scripts/trigger_analysis.py --recent 7     # last 7 days
    python3 scripts/trigger_analysis.py --json         # machine-readable

Designed to run periodically (weekly?) over recent transcripts. A regression
in the skill:MCP ratio for a given family is the canonical signal that a
SKILL.md description rewrite is overdue.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

TRANSCRIPT_ROOT_DEFAULT = Path.home() / ".claude/projects"

# Plugins we care about (the retritis MCP families). Adjust if more land.
KNOWN_PLUGINS = ["jetsam", "blq", "fledgling", "squackit", "lackpy", "kibitzer", "agent_riggs"]

# Non-retritis MCP servers that show up in scratch/demo sessions (e.g. the
# `cosmic-mcp-hello` FastMCP example invoked from /tmp). They are not plugins;
# filter them so they don't pollute the report. Unknown-but-real plugins are
# still auto-discovered — only these named demos are dropped.
IGNORED_PLUGINS = {"hello"}

# Verbs that are explicit low-level passthrough / escape-hatch tools rather than
# skill-routed workflow verbs. Using them is NOT a sign the SKILL.md routing
# failed — they exist precisely for cases the workflow verbs don't cover (e.g.
# jetsam's `git` proxy for cross-repo `git -C`). They are excluded from the
# bypass-ratio denominator so a heavily-passthrough plugin isn't mislabeled
# BYPASSED; they still appear in the MCP totals for transparency.
PASSTHROUGH_VERBS: dict[str, set[str]] = {
    "jetsam": {"git"},
}

MCP_TOOL_RE = re.compile(r"^mcp__(?:plugin_)?(\w+?)(?:_\w+)?__(\w+)$")


@dataclass
class PluginStats:
    name: str
    skill_calls: int = 0
    mcp_calls: int = 0
    mcp_by_verb: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def passthrough_calls(self) -> int:
        """MCP calls to explicit passthrough/escape-hatch verbs (see
        PASSTHROUGH_VERBS) — excluded from the bypass-ratio denominator."""
        verbs = PASSTHROUGH_VERBS.get(self.name, set())
        return sum(n for v, n in self.mcp_by_verb.items() if v in verbs)

    @property
    def routed_calls(self) -> int:
        """MCP calls the skill is meant to route — total minus passthrough."""
        return self.mcp_calls - self.passthrough_calls

    @property
    def ratio(self) -> float:
        """Skill calls per *routed* MCP call (passthrough verbs excluded).

        ratio = 0       → skill never fired, all routed access was direct
        ratio = 1       → exactly one Skill per routed MCP (overkill, but discoverable)
        ratio in (0,1)  → skill fires sometimes; the typical healthy band is
                          0.05..0.5 since one Skill load covers many MCP calls
        """
        return self.skill_calls / self.routed_calls if self.routed_calls else float("nan")

    @property
    def health(self) -> str:
        # UNUSED: no signal at all in this corpus.
        if self.mcp_calls == 0 and self.skill_calls == 0:
            return "UNUSED"
        # BYPASSED: heavy routed usage but the Skill umbrella NEVER fired — the
        # canonical "SKILL.md routing table never reaches the model" case. Keyed
        # on skill_calls == 0 (the documented premise), not a ratio floor, so a
        # plugin whose skill *does* fire isn't mislabeled merely for high volume
        # (one Skill load legitimately covers many downstream calls). Passthrough
        # verbs are already excluded from routed_calls.
        if self.routed_calls > 20 and self.skill_calls == 0:
            return "BYPASSED"
        # LOW: some routed MCP, no Skill. Could be small-sample noise OR an
        # early-warning sign that the description doesn't match user phrasing.
        if self.skill_calls == 0 and self.routed_calls > 5:
            return "LOW"
        if self.skill_calls == 0:
            return "INCIDENTAL"
        return "ENGAGED"


def iter_tool_uses(transcript: Path) -> Iterable[dict]:
    """Yield every tool_use block found in a Claude Code transcript JSONL."""
    try:
        text = transcript.read_text()
    except (OSError, UnicodeDecodeError):
        return
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block


def classify_tool_call(name: str) -> tuple[str | None, str | None]:
    """Return (plugin, verb) for an MCP tool name, or (None, None) for non-MCP."""
    m = MCP_TOOL_RE.match(name)
    if not m:
        return None, None
    plugin_raw, verb = m.group(1), m.group(2)
    # Normalize: `mcp__plugin_blq_blq_mcp__run` → "blq"
    plugin = plugin_raw.split("_")[0]
    return plugin, verb


def analyze(transcripts: list[Path]) -> dict[str, PluginStats]:
    stats: dict[str, PluginStats] = {p: PluginStats(name=p) for p in KNOWN_PLUGINS}

    for t in transcripts:
        for block in iter_tool_uses(t):
            name = block.get("name", "")
            if name == "Skill":
                # Skill tool: the `skill` arg names which skill was invoked.
                inp = block.get("input", {}) or {}
                skill_name = (inp.get("skill") or "").strip()
                # skill name shape: "jetsam:jetsam-workflow" or "jetsam-workflow"
                target = skill_name.split(":")[-1].replace("-workflow", "").replace("-", "_")
                if target in stats:
                    stats[target].skill_calls += 1
                continue
            plugin, verb = classify_tool_call(name)
            if plugin is None or plugin in IGNORED_PLUGINS:
                continue
            # Normalize agent_riggs <-> agent-riggs
            key = "agent_riggs" if plugin in ("agent_riggs", "agentriggs") else plugin
            if key not in stats:
                stats[key] = PluginStats(name=key)
            stats[key].mcp_calls += 1
            stats[key].mcp_by_verb[verb] += 1
    return stats


def discover_transcripts(arg_paths: list[str], recent_days: int | None) -> list[Path]:
    if arg_paths:
        return [Path(p).expanduser() for p in arg_paths]
    if not TRANSCRIPT_ROOT_DEFAULT.exists():
        return []
    cutoff = (time.time() - recent_days * 86400) if recent_days else 0
    out: list[Path] = []
    for jsonl in TRANSCRIPT_ROOT_DEFAULT.rglob("*.jsonl"):
        try:
            if jsonl.stat().st_mtime >= cutoff:
                out.append(jsonl)
        except OSError:
            continue
    return out


def render_text(stats: dict[str, PluginStats], transcripts: list[Path]) -> tuple[str, int]:
    out = [f"Transcripts analyzed: {len(transcripts)}", ""]
    # Header
    out.append(f"{'plugin':<14} {'health':<11} {'Skill':>6} {'MCP':>6} {'ratio':>8}  top verbs")
    out.append("-" * 78)
    any_bypassed = False
    for plugin, s in sorted(stats.items()):
        health = s.health
        pt_verbs = PASSTHROUGH_VERBS.get(plugin, set())
        if health == "UNUSED":
            ratio_s = "—"
            top = "—"
        else:
            ratio_s = f"{s.ratio:.3f}" if s.routed_calls else "—"
            top_verbs = sorted(s.mcp_by_verb.items(), key=lambda x: -x[1])[:3]
            top = ", ".join(f"{v}×{n}" + (" [passthrough]" if v in pt_verbs else "")
                            for v, n in top_verbs)
        out.append(f"{plugin:<14} {health:<11} {s.skill_calls:>6} {s.mcp_calls:>6} {ratio_s:>8}  {top}")
        if health == "BYPASSED":
            any_bypassed = True
    out.append("")
    out.append("Legend:")
    out.append("  ENGAGED    The skill umbrella fires regularly relative to MCP usage.")
    out.append("  LOW        Some MCP usage, no Skill calls — could be small sample, could be description gap.")
    out.append("  BYPASSED   >20 routed MCP calls, 0 Skill invocations — SKILL.md trigger language never matched.")
    out.append("             (passthrough verbs like jetsam `git` are excluded from the routed count.)")
    out.append("  INCIDENTAL Trivial MCP usage with no Skill — too few samples to judge.")
    out.append("  UNUSED     No activity in this corpus.")
    out.append("")
    out.append("Action: BYPASSED plugins are the highest-ROI targets for SKILL.md description rewrites.")
    out.append("        LOW plugins are watchlist material — re-check after a few more sessions.")
    rc = 1 if any_bypassed else 0
    return "\n".join(out), rc


def render_json(stats: dict[str, PluginStats], transcripts: list[Path]) -> tuple[str, int]:
    payload = {
        "transcripts": len(transcripts),
        "plugins": {
            p: {
                "skill_calls": s.skill_calls,
                "mcp_calls": s.mcp_calls,
                "passthrough_calls": s.passthrough_calls,
                "routed_calls": s.routed_calls,
                "ratio": s.ratio if s.routed_calls else None,
                "health": s.health,
                "top_verbs": dict(sorted(s.mcp_by_verb.items(), key=lambda x: -x[1])[:5]),
            }
            for p, s in sorted(stats.items())
        },
    }
    return json.dumps(payload, indent=2), 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("transcripts", nargs="*", help="transcript JSONL paths (default: discover under ~/.claude/projects)")
    p.add_argument("--recent", type=int, default=None, metavar="DAYS",
                   help="when auto-discovering, only include transcripts modified in the last N days")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    transcripts = discover_transcripts(args.transcripts, args.recent)
    if not transcripts:
        print("No transcripts found.", file=sys.stderr)
        return 1
    stats = analyze(transcripts)
    body, rc = render_json(stats, transcripts) if args.json else render_text(stats, transcripts)
    print(body)
    return rc


if __name__ == "__main__":
    sys.exit(main())
