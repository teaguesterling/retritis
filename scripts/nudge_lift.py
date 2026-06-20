#!/usr/bin/env python3
"""Compute nudge lift from kibitzer's A/B trial log.

kibitzer (with experiment.nudge_probability < 1.0) randomly NUDGES vs leaves a
silent CONTROL on each eligible bypass, then records — per trial — whether the
agent used the suggested structured tool within the heed window. This reads
~/.kibitzer/nudge_trials.jsonl and reports, per plugin and overall:

  heed(nudge)   = P(used the suggested tool in time | NUDGED)
  heed(control) = same | silent CONTROL
  lift          = heed(nudge) - heed(control)   ← the causal effect of the nudge

Lift ≈ 0 at adequate N means the nudge doesn't change behavior. Trials that
never resolved (session ended mid-window) are simply absent (conservative).

Usage: python3 scripts/nudge_lift.py [path-to-nudge_trials.jsonl]
"""
from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path

LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".kibitzer" / "nudge_trials.jsonl"


def main() -> int:
    if not LOG.exists():
        print(f"no trial log at {LOG}")
        print("Run with kibitzer enabled and experiment.nudge_probability < 1.0, "
              "then let some sessions accumulate.")
        return 0

    # counts[plugin][arm] = [heeded, total]
    counts: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: {"nudge": [0, 0], "control": [0, 0]})
    for line in LOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        arm = r.get("arm")
        if arm not in ("nudge", "control"):
            continue
        c = counts[r.get("plugin", "?")][arm]
        c[1] += 1
        if r.get("heed"):
            c[0] += 1

    def rate(c: list[int]) -> float:
        return (c[0] / c[1]) if c[1] else float("nan")

    def cell(c: list[int]) -> str:
        return f"{rate(c):.0%} ({c[0]}/{c[1]})" if c[1] else "— (0)"

    def lift_str(n: list[int], ctl: list[int]) -> str:
        if not (n[1] and ctl[1]):
            return "—"
        return f"{rate(n) - rate(ctl):+.0%}"

    print(f"nudge A/B lift — {LOG}\n")
    print(f"{'plugin':12} {'heed(nudge)':>18} {'heed(control)':>18} {'lift':>7}")
    print("-" * 60)
    total = {"nudge": [0, 0], "control": [0, 0]}
    for plugin, arms in sorted(counts.items()):
        n, ctl = arms["nudge"], arms["control"]
        for a in ("nudge", "control"):
            total[a][0] += arms[a][0]
            total[a][1] += arms[a][1]
        print(f"{plugin:12} {cell(n):>18} {cell(ctl):>18} {lift_str(n, ctl):>7}")
    print("-" * 60)
    n, ctl = total["nudge"], total["control"]
    print(f"{'OVERALL':12} {cell(n):>18} {cell(ctl):>18} {lift_str(n, ctl):>7}")
    print("\nlift = heed(nudge) − heed(control). Near 0 (at adequate N) means the")
    print("nudge isn't changing behavior. Unresolved trials are excluded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
