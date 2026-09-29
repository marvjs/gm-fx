"""Robustness JSON export tests."""

import json
from pathlib import Path

from grandmaster_fx.research.robustness import AblationResult, StabilitySummary
from grandmaster_fx.research.robustness_exports import export_robustness


def test_export_robustness_writes_json(tmp_path: Path) -> None:
    stability = StabilitySummary(2, 1, 50, 10, -5, 12, 0.9, False)
    path = export_robustness(
        "EURUSDm",
        tmp_path,
        (),
        stability,
        (),
        (AblationResult("BUY", 5, -2, -0.4, 40),),
    )
    payload = json.loads(path.read_text())
    assert payload["symbol"] == "EURUSDm"
    assert payload["stability"]["stable"] is False
    assert payload["ablations"][0]["label"] == "BUY"
