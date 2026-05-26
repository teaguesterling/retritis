"""Per-run metric record + jsonl IO. One RunRecord per (scenario, integrations, run).

Mirrors the schema in vision/phase-4-calibration.md section C. Pure data — the
extractors that *populate* these from a captured agent trace are stubbed where
they depend on integrations that don't exist yet (marked TODO).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from statistics import mean, pstdev


@dataclass
class RunRecord:
    scenario: str
    integrations: str                 # label, e.g. "baseline" or "CB"
    run: int
    passed: bool = False              # check.py verdict
    # cost (workstream A)
    turns: int | None = None
    tokens: int | None = None
    walltime_s: float | None = None
    # substrate (workstream C)
    tool_latencies_ms: list[float] = field(default_factory=list)
    coaching_fired: int = 0
    doc_context_coaching_fired: int = 0
    staleness_violation: bool = False
    # policy (workstream B)
    policy_verdict: dict | None = None      # {"kibitzer":..,"lackpy":..,"truth":..}
    # learn loop (workstream A)
    surfaced_fix: str | None = None
    took_surfaced_fix: bool = False
    surfaced_fix_correct: bool | None = None
    detail: str = ""

    def p95_latency(self) -> float | None:
        xs = sorted(self.tool_latencies_ms)
        return xs[int(0.95 * (len(xs) - 1))] if xs else None


def write_records(records: list[RunRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(asdict(r)) + "\n")


def read_records(path: Path) -> list[RunRecord]:
    return [RunRecord(**json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def agg(values: list[float]) -> dict:
    """mean +/- stdev for a metric across runs (the unit of T3 judgement)."""
    vs = [v for v in values if v is not None]
    return {"n": len(vs), "mean": mean(vs) if vs else None, "stdev": pstdev(vs) if len(vs) > 1 else 0.0}
