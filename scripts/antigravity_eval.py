#!/usr/bin/env python3
"""Evaluate Retritis tool and skill usage across Antigravity (AGY) transcripts.

Scans Antigravity conversation transcripts in ~/.gemini/antigravity-cli/brain/
and measures:
  1. Direct MCP / structured tool invocations (squackit, blq, jetsam, fledgling, etc.)
  2. Skill lookups (viewing SKILL.md for Retritis workflows)
  3. Raw shell / standard tool bypasses:
     - raw git commands (git commit, git add, git push) vs jetsam
     - raw test/build commands (pytest, cargo test, npm test) vs blq
     - raw grep/find in run_command vs squackit/fledgling
  4. Tool adoption and bypass ratios

Usage:
    python3 scripts/antigravity_eval.py
    python3 scripts/antigravity_eval.py --recent-days 7
    python3 scripts/antigravity_eval.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BRAIN_DIR = Path.home() / ".gemini/antigravity-cli/brain"

# Regexes for classifying raw shell commands executed via run_command
GIT_BYPASS_RE = re.compile(r"\bgit\s+(?:add|commit|push|rebase|status|diff|checkout|switch)\b")
BUILD_BYPASS_RE = re.compile(r"\b(?:pytest|cargo\s+(?:test|build)|npm\s+(?:test|run\s+build)|make|go\s+test|mvn\s+test)\b")
SEARCH_BYPASS_RE = re.compile(r"\b(?:grep|rg|find|ack|ag)\b")

SKILL_MD_RE = re.compile(r"/skills/([^/]+)/SKILL\.md")


@dataclass
class EvaluationStats:
    total_conversations: int = 0
    total_steps: int = 0
    
    # Tool calls count
    mcp_calls: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    standard_tool_calls: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    skill_activations: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Bypass counts
    git_bypasses: int = 0
    build_bypasses: int = 0
    search_bypasses: int = 0
    
    # Detailed bypass commands
    bypass_samples: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def analyze_transcript(transcript_path: Path, stats: EvaluationStats) -> None:
    stats.total_conversations += 1
    
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                stats.total_steps += 1
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                
                # Check tool calls
                tool_calls = entry.get("tool_calls", [])
                if not isinstance(tool_calls, list):
                    continue
                    
                for call in tool_calls:
                    name = call.get("name", "")
                    args = call.get("args", {})
                    
                    # 1. Retritis MCP tool calls (both native mcp_* and call_mcp_tool)
                    if name == "call_mcp_tool":
                        server = args.get("ServerName", "")
                        tool = args.get("ToolName", "")
                        full_name = f"mcp__{server}__{tool}"
                        stats.mcp_calls[full_name] += 1
                    elif any(name.startswith(p) for p in ["mcp_squackit", "mcp_blq", "mcp_jetsam", "mcp_fledgling", "mcp_kibitzer", "mcp_lackpy", "squackit", "blq", "jetsam", "fledgling", "kibitzer", "lackpy"]):
                        stats.mcp_calls[name] += 1
                    elif name in ["grep_search", "find_by_name", "run_command", "view_file", "list_dir"]:
                        stats.standard_tool_calls[name] += 1
                    else:
                        stats.standard_tool_calls[name] += 1
                    
                    # 2. Skill inspection (e.g. view_file on SKILL.md)
                    if name == "view_file":
                        path = args.get("AbsolutePath", "")
                        match = SKILL_MD_RE.search(path)
                        if match:
                            skill_name = match.group(1)
                            stats.skill_activations[skill_name] += 1
                            
                    # 3. Raw shell bypass detection
                    if name == "run_command":
                        cmd = args.get("CommandLine", "")
                        if GIT_BYPASS_RE.search(cmd):
                            stats.git_bypasses += 1
                            if len(stats.bypass_samples["git"]) < 5:
                                stats.bypass_samples["git"].append(cmd.strip()[:80])
                        if BUILD_BYPASS_RE.search(cmd):
                            stats.build_bypasses += 1
                            if len(stats.bypass_samples["build"]) < 5:
                                stats.bypass_samples["build"].append(cmd.strip()[:80])
                        if SEARCH_BYPASS_RE.search(cmd):
                            stats.search_bypasses += 1
                            if len(stats.bypass_samples["search"]) < 5:
                                stats.bypass_samples["search"].append(cmd.strip()[:80])

    except Exception as e:
        print(f"Error reading {transcript_path}: {e}", file=sys.stderr)


def collect_transcripts(brain_dir: Path, max_age_days: int | None = None) -> list[Path]:
    if not brain_dir.exists():
        return []
    
    transcripts = []
    now = datetime.now(timezone.utc).timestamp()
    
    for log_path in brain_dir.glob("*/.system_generated/logs/transcript.jsonl"):
        if max_age_days is not None:
            mtime = log_path.stat().st_mtime
            if (now - mtime) > (max_age_days * 86400):
                continue
        transcripts.append(log_path)
        
    return sorted(transcripts)


def print_report(stats: EvaluationStats) -> None:
    print("=" * 70)
    print(" 🦅 RETRITIS HARNESS ADOPTION & EVALUATION REPORT (Antigravity)")
    print("=" * 70)
    print(f"Conversations Analyzed : {stats.total_conversations}")
    print(f"Total Trajectory Steps : {stats.total_steps}")
    print("-" * 70)
    
    print("\n📦 RETRITIS MCP TOOL USAGE:")
    if stats.mcp_calls:
        for tool, count in sorted(stats.mcp_calls.items(), key=lambda x: -x[1]):
            print(f"  • {tool:<35} : {count:>4} calls")
    else:
        print("  (No direct Retritis MCP tool calls detected yet)")
        
    print("\n📖 SKILL ACTIVATIONS:")
    if stats.skill_activations:
        for skill, count in sorted(stats.skill_activations.items(), key=lambda x: -x[1]):
            print(f"  • {skill:<35} : {count:>4} activations")
    else:
        print("  (No skill activations recorded)")
        
    print("\n⚠️  STRUCTURED TOOL BYPASS METRICS (Raw Shell vs Retritis):")
    
    # Git
    jetsam_calls = sum(c for t, c in stats.mcp_calls.items() if "jetsam" in t)
    total_git = jetsam_calls + stats.git_bypasses
    git_bypass_pct = (stats.git_bypasses / total_git * 100) if total_git else 0.0
    print(f"  • Git Operations : {jetsam_calls} jetsam calls vs {stats.git_bypasses} raw git commands (Bypass: {git_bypass_pct:.1f}%)")
    for s in stats.bypass_samples["git"][:2]:
        print(f"      sample: `{s}`")
        
    # Build / Test
    blq_calls = sum(c for t, c in stats.mcp_calls.items() if "blq" in t)
    total_build = blq_calls + stats.build_bypasses
    build_bypass_pct = (stats.build_bypasses / total_build * 100) if total_build else 0.0
    print(f"  • Build & Test   : {blq_calls} blq calls vs {stats.build_bypasses} raw test commands (Bypass: {build_bypass_pct:.1f}%)")
    for s in stats.bypass_samples["build"][:2]:
        print(f"      sample: `{s}`")
        
    # Code Search
    squackit_calls = sum(c for t, c in stats.mcp_calls.items() if "squackit" in t or "fledgling" in t)
    standard_search = stats.standard_tool_calls.get("grep_search", 0) + stats.standard_tool_calls.get("find_by_name", 0) + stats.search_bypasses
    total_search = squackit_calls + standard_search
    search_bypass_pct = (standard_search / total_search * 100) if total_search else 0.0
    print(f"  • Code Search    : {squackit_calls} squackit calls vs {standard_search} raw search/grep (Bypass: {search_bypass_pct:.1f}%)")
    for s in stats.bypass_samples["search"][:2]:
        print(f"      sample: `{s}`")

    print("\n" + "=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Retritis adoption in Antigravity.")
    parser.add_argument("--brain-dir", type=Path, default=DEFAULT_BRAIN_DIR, help="Path to Antigravity brain dir")
    parser.add_argument("--recent-days", type=int, default=None, help="Limit to transcripts modified within N days")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    
    args = parser.parse_args()
    
    transcripts = collect_transcripts(args.brain_dir, args.recent_days)
    stats = EvaluationStats()
    for t in transcripts:
        analyze_transcript(t, stats)
        
    if args.json:
        payload = {
            "conversations": stats.total_conversations,
            "steps": stats.total_steps,
            "mcp_calls": dict(stats.mcp_calls),
            "standard_tool_calls": dict(stats.standard_tool_calls),
            "skill_activations": dict(stats.skill_activations),
            "bypasses": {
                "git": stats.git_bypasses,
                "build": stats.build_bypasses,
                "search": stats.search_bypasses,
            }
        }
        print(json.dumps(payload, indent=2))
    else:
        print_report(stats)
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
