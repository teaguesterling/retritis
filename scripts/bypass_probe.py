#!/usr/bin/env python3
"""Scoped probe: do retritis-tool-using sessions still reach for raw Bash?

Measures the *counterfactual* the SKILLs (and kibitzer) are meant to win — how
often a session that demonstrably had a retritis server loaded (>=1 retritis MCP
call) still ran a raw Bash op that a workflow verb covers. Conservative by
design (mirrors the trigger_analysis PASSTHROUGH lesson):

  * Denominator = sessions with >=1 retritis call AND not in the retritis repo
    (excludes maintenance sessions where shell git/grep is legitimate).
  * Availability proxy = ">=1 retritis call in session". UNDERCOUNTS: a session
    that went all-Bash with the server silently loaded is invisible here.
  * Genuine bypass only = in-cwd ops a verb covers. Excludes pipe-filter greps,
    `git -C`, read-only git (log/diff/show), and exotic passthrough.

Not a CI gate — a probe to eyeball whether the preference signal is real.

Usage:  python3 scripts/bypass_probe.py [WINDOW_DAYS]   (default 14)
"""
from __future__ import annotations
import json, re, sys, time
from collections import defaultdict
from pathlib import Path

ROOT = Path.home() / ".claude/projects"
WINDOW_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 14

RETRITIS = {"blq", "jetsam", "fledgling", "squackit", "lackpy", "kibitzer", "agent_riggs", "agentriggs"}
MCP_RE = re.compile(r"^mcp__(?:plugin_)?(\w+?)(?:_\w+)?__(\w+)$")


def classify_bash(cmd: str) -> str | None:
    """Conservative: only count primary ops a workflow verb covers in-cwd."""
    c = cmd.strip()
    first = c.split("&&")[0].split("|")[0].strip()  # first stage only
    if re.match(r"^(grep\s+-[A-Za-z]*r[A-Za-z]*\b|rg\b|ag\b|ack\b)", first):
        return "squackit:search"
    if re.match(r"^find\b.*-name\b", first):
        return "squackit:find"
    m = re.match(r"^git\s+(?!-C\b)([a-z-]+)", first)
    if m and m.group(1) in {"status", "add", "commit", "push", "pull", "fetch",
                            "checkout", "switch", "merge", "stash"}:
        return f"jetsam:{m.group(1)}"
    if re.match(r"^(pytest|py\.test|tox|make|cargo\s+(test|build)|npm\s+(test|run)|go\s+test|mypy|ruff)\b", first):
        return "blq:run"
    return None


def iter_blocks(p: Path):
    try:
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = rec.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("content"), list):
                for b in msg["content"]:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        yield b
    except (OSError, UnicodeDecodeError):
        return


cutoff = time.time() - WINDOW_DAYS * 86400
sessions_total = sessions_qualified = 0
bypass = defaultdict(int)
retritis_calls = defaultdict(int)
examples = defaultdict(list)

for jf in ROOT.rglob("*.jsonl"):
    try:
        if jf.stat().st_mtime < cutoff:
            continue
    except OSError:
        continue
    if "retritis" in jf.parent.name:        # exclude maintenance sessions
        continue
    sessions_total += 1
    rcalls = defaultdict(int)
    bash_cmds = []
    for b in iter_blocks(jf):
        name = b.get("name", "")
        if name == "Bash":
            cmd = (b.get("input", {}) or {}).get("command", "")
            if cmd:
                bash_cmds.append(cmd)
            continue
        m = MCP_RE.match(name)
        if m:
            plug = m.group(1).split("_")[0]
            plug = "agent_riggs" if plug in ("agentriggs", "agent") else plug
            if plug in RETRITIS:
                rcalls[plug] += 1
    if not rcalls:                # availability proxy: server proven loaded
        continue
    sessions_qualified += 1
    for plug, n in rcalls.items():
        retritis_calls[plug] += n
    for cmd in bash_cmds:
        cat = classify_bash(cmd)
        if cat:
            bypass[cat] += 1
            if len(examples[cat]) < 3:
                examples[cat].append(cmd.strip()[:90])

print(f"window: last {WINDOW_DAYS}d | transcripts scanned (non-retritis): {sessions_total}")
print(f"qualifying sessions (>=1 retritis call): {sessions_qualified}")
print("  NOTE: undercounts — all-Bash sessions with the server silently loaded are invisible.\n")
print("=== retritis tool calls in qualifying sessions ===")
for p, n in sorted(retritis_calls.items(), key=lambda x: -x[1]):
    print(f"  {p:12} {n}")
print("\n=== genuine Bash bypasses (a verb covered it, in-cwd) ===")
if not bypass:
    print("  (none) — no raw-shell fallback detected in qualifying sessions.")
for cat, n in sorted(bypass.items(), key=lambda x: -x[1]):
    print(f"  {cat:18} {n:4}   e.g. {examples[cat][0] if examples[cat] else ''}")
