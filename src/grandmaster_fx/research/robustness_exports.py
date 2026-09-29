"""Machine-readable robustness research exports."""

import json
from dataclasses import asdict
from pathlib import Path

from grandmaster_fx.research.models import SensitivityRun, WalkForwardFold
from grandmaster_fx.research.robustness import AblationResult, StabilitySummary


def export_robustness(
    symbol: str,
    directory: Path,
    folds: tuple[WalkForwardFold, ...],
    stability: StabilitySummary,
    sensitivity: tuple[SensitivityRun, ...],
    ablation: tuple[AblationResult, ...],
) -> Path:
    """Write one JSON report containing every robustness result."""
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{symbol}_robustness.json"
    payload = {
        "symbol": symbol,
        "stability": asdict(stability),
        "walk_forward": [
            {
                "number": item.number,
                "train_start": item.train_start,
                "train_end": item.train_end,
                "test_start": item.test_start,
                "test_end": item.test_end,
                "metrics": asdict(item.result.metrics),
            }
            for item in folds
        ],
        "sensitivity": [
            {"label": item.label, "metrics": asdict(item.result.metrics)} for item in sensitivity
        ],
        "ablations": [asdict(item) for item in ablation],
    }
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination
