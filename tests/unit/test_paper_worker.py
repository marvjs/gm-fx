"""Paper worker lifecycle tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from grandmaster_fx.domain.market_data import Bar, Tick, Timeframe
from grandmaster_fx.paper.config import load_paper_worker_settings
from grandmaster_fx.paper.models import PaperPosition, PaperState
from grandmaster_fx.paper.state import PaperStateStore
from grandmaster_fx.paper.worker import PaperWorker
from grandmaster_fx.strategies.models import Signal


class Market:
    def __init__(self) -> None:
        self.price = 1.1

    def tick(self, _name: str) -> Tick:
        return Tick(datetime.now(UTC), self.price, self.price + 0.0001, self.price, 1)

    def bars(self, _name: str, _timeframe: Timeframe, count: int, _start: int = 1) -> list[Bar]:
        base = datetime.now(UTC) - timedelta(minutes=5 * count)
        return [
            Bar(
                base + timedelta(minutes=5 * i),
                1 + i * 0.00015,
                1.001 + i * 0.00015,
                0.999 + i * 0.00015,
                1 + i * 0.00015,
                1,
                5,
                0,
            )
            for i in range(count)
        ]


def test_state_round_trip(tmp_path: Path) -> None:
    store = PaperStateStore(tmp_path / "state.json")
    state = PaperState(
        1000,
        positions=[
            PaperPosition(
                "EURUSDm",
                Signal.BUY,
                1,
                1.1,
                0.9,
                1.2,
                0.0001,
                0.01,
                0.8,
                datetime.now(UTC).isoformat(),
            )
        ],
    )
    store.save(state)
    assert store.load(1000).positions[0].symbol == "EURUSDm"


def test_cycle_opens_and_then_closes_at_small_profit(tmp_path: Path) -> None:
    market = Market()
    settings = load_paper_worker_settings()
    store = PaperStateStore(tmp_path / "state.json")
    worker = PaperWorker(market, (("EURUSDm", 0.0001),), settings, store, tmp_path / "STOP")
    first = worker.cycle()
    assert first["opened"] == ["EURUSDm"]
    market.price = 1.12
    second = worker.cycle()
    assert second["closed"] == ["EURUSDm"]


def test_stop_file(tmp_path: Path) -> None:
    worker = PaperWorker(
        Market(),
        (),
        load_paper_worker_settings(),
        PaperStateStore(tmp_path / "state.json"),
        tmp_path / "STOP",
    )
    worker.request_stop()
    assert (tmp_path / "STOP").is_file()
