"""Phase 4 calibration/benchmark configuration.

See vision/phase-4-calibration.md. A run is the cross product of
(scenario, integration-set, run-index). OFF = baseline; the calibration pass
runs everything OFF to derive the T3 bars before any workstream is built.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# The three integrations under test, keyed as the calibration doc uses them.
INTEGRATIONS = ("C", "B", "A")  # persistent substrate / one-policy-two-enforcers / learn loop


@dataclass
class CalibrationConfig:
    scenarios: list[str]                       # corpus ids, e.g. ["S01_toolinfo_subscript"]
    integrations: dict[str, bool] = field(     # OFF baseline by default
        default_factory=lambda: {k: False for k in INTEGRATIONS}
    )
    n_runs: int = 5                            # statistical validity: report mean +/- stdev
    model: str = "qwen3:14b-iq4xs"             # local GPU on longbottom; fix seed where possible
    runner_mode: str = "proxy"                 # "proxy" (first-action scoring) | "full" (drive a real agent)
    corpus_dir: Path = Path(__file__).parent / "corpus"
    out_dir: Path = Path(__file__).parent / "results"
    fixtures_root: Path = Path.home() / "Projects"   # where fixture repos (fledgling, ...) live

    def label(self) -> str:
        on = "".join(k for k in INTEGRATIONS if self.integrations.get(k))
        return f"{self.runner_mode}.{on or 'baseline'}"
