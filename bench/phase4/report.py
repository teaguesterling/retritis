"""Aggregate results/*.jsonl into a markdown report: mean +/- stdev per metric,
off-vs-on deltas, and (once bars are pinned) bar verdicts.

Used twice: at calibration (OFF only -> baseline distributions feed bar-pinning),
and per workstream (OFF vs ON -> did the bar clear). A bar within one stdev of
baseline is NOT cleared (calibration doc, binding honesty rule).
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from metrics import read_records, agg


def collect(results_dir: Path):
    by_int: dict[str, list] = defaultdict(list)
    for jl in sorted(results_dir.glob("*.jsonl")):
        for r in read_records(jl):
            by_int[r.integrations].append(r)
    return by_int


def render(results_dir: Path) -> str:
    by_int = collect(results_dir)
    out = ["# Phase 4 benchmark report", ""]
    if not by_int:
        return "\n".join(out + ["_no results yet — run runner.py and write records to results/_"])
    for label, recs in sorted(by_int.items()):
        n = len(recs)
        pass_rate = sum(r.passed for r in recs) / n if n else 0
        turns = agg([r.turns for r in recs])
        tokens = agg([r.tokens for r in recs])
        wall = agg([r.walltime_s for r in recs])
        p95 = agg([r.p95_latency() for r in recs])
        out += [
            f"## `{label}`  (n={n})",
            f"- pass rate: {pass_rate:.0%}",
            f"- turns: mean {turns['mean']} +/- {turns['stdev']}",
            f"- tokens: mean {tokens['mean']} +/- {tokens['stdev']}",
            f"- walltime_s: mean {wall['mean']} +/- {wall['stdev']}",
            f"- p95 tool latency (ms): mean {p95['mean']} +/- {p95['stdev']}",
            f"- coaching fired (total): {sum(r.coaching_fired for r in recs)} "
            f"(doc-context: {sum(r.doc_context_coaching_fired for r in recs)})",
            f"- staleness violations: {sum(r.staleness_violation for r in recs)}",
            "",
        ]
    out += ["> Bars are calibrated in vision/phase-4-baseline.md from the `baseline` block above.",
            "> A metric within one stdev of baseline does not clear its bar."]
    return "\n".join(out)


if __name__ == "__main__":
    rd = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results"
    print(render(rd))
