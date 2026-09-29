"""Consolidated candidate-pack tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.candidate_pack import (
    load_channel_mean_reversion,
    load_fibonacci_pullback,
    load_momentum_continuation,
    load_session_range_breakout,
)

LOADERS = (
    (load_session_range_breakout, "session_range_breakout.toml", "session_range_breakout"),
    (load_fibonacci_pullback, "fibonacci_pullback.toml", "fibonacci_pullback"),
    (load_channel_mean_reversion, "channel_mean_reversion.toml", "channel_mean_reversion"),
    (load_momentum_continuation, "momentum_continuation.toml", "momentum_continuation"),
)


def bars(count: int = 100) -> list[Bar]:
    start = datetime(2026, 1, 1, 6, tzinfo=UTC)
    return [
        Bar(start + timedelta(minutes=5 * i), 1, 1.001, 0.999, 1, 10, 5, 0) for i in range(count)
    ]


def test_all_candidates_load_and_prepare() -> None:
    for loader, filename, identifier in LOADERS:
        strategy = loader(Path("configs/strategies") / filename)
        assert strategy.identifier == identifier
        context = strategy.prepare(bars())
        assert len(context.close) == 100


def test_all_candidates_reject_wrong_context() -> None:
    for loader, filename, _identifier in LOADERS:
        strategy = loader(Path("configs/strategies") / filename)
        with pytest.raises(TypeError, match="CandidateContext"):
            strategy.evaluate_at("EURUSDm", bars(), 99, 0.00001, object())
