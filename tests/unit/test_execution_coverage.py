"""Coverage for demo and paper execution support modules."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from grandmaster_fx.config.demo_execution import load_demo_execution_settings
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.execution.journal import ExecutionJournal
from grandmaster_fx.execution.models import ExecutionCandidate, PositionSnapshot
from grandmaster_fx.paper.config import load_paper_worker_settings
from grandmaster_fx.paper.models import PaperPosition, PaperState
from grandmaster_fx.paper.state import PaperStateStore
from grandmaster_fx.paper.worker import PaperWorker
from grandmaster_fx.strategies.models import Signal


def test_execution_candidate_validation() -> None:
    with pytest.raises(ValueError, match="BUY or SELL"):
        ExecutionCandidate("EURUSDm", Signal.HOLD, 0.5, 1.0, 0.9, 1.1)
    with pytest.raises(ValueError, match="between zero and one"):
        ExecutionCandidate("EURUSDm", Signal.BUY, 2.0, 1.0, 0.9, 1.1)


def test_position_snapshot_mapping() -> None:
    result = PositionSnapshot.from_mapping(
        {
            "ticket": 7,
            "symbol": "EURUSDm",
            "type": 0,
            "volume": 0.01,
            "price_open": 1.0,
            "price_current": 1.1,
            "sl": 0.9,
            "tp": 1.2,
            "profit": 1.0,
            "magic": 771100,
            "time": 1_700_000_000,
        }
    )
    assert result.ticket == 7
    assert result.signal is Signal.BUY


def test_execution_journal_writes_json_line(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ExecutionJournal(path)
    journal.append("opened", symbol="EURUSDm")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["event"] == "opened"
    assert payload["symbol"] == "EURUSDm"


def test_invalid_execution_configs_are_wrapped(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.toml"
    invalid.write_text("[execution]\nenabled=true\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Demo execution"):
        load_demo_execution_settings(invalid)
    with pytest.raises(ConfigurationError, match="Paper worker"):
        load_paper_worker_settings(invalid)


def test_paper_state_defaults_and_profit() -> None:
    position = PaperPosition(
        "EURUSDm",
        Signal.BUY,
        1.0,
        1.01,
        0.99,
        1.02,
        0.0001,
        0.01,
        0.8,
        datetime.now(UTC).isoformat(),
    )
    state = PaperState(1000.0, positions=[position])
    assert position.profit == pytest.approx(1.0)
    assert state.floating_profit == pytest.approx(1.0)
    assert state.equity == pytest.approx(1001.0)


def test_state_store_missing_file_returns_initial_balance(tmp_path: Path) -> None:
    state = PaperStateStore(tmp_path / "missing.json").load(1234.0)
    assert state.balance == 1234.0
    assert state.positions == []


def test_paper_run_honors_maximum_cycles(tmp_path: Path) -> None:
    settings = load_paper_worker_settings()
    worker = PaperWorker(
        Mock(), (), settings, PaperStateStore(tmp_path / "state.json"), tmp_path / "STOP"
    )
    worker.run(maximum_cycles=1)
    assert (tmp_path / "state.json").is_file()
