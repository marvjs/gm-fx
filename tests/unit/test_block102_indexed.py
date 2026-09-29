"""Block 10.2 indexed evaluation tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.experiments.diagnostics import collect_diagnostics
from grandmaster_fx.strategies.volatility_expansion import load_volatility_expansion


def bars() -> list[Bar]:
    start = datetime(2026, 1, 1, 6, tzinfo=UTC)
    return [
        Bar(
            start + timedelta(minutes=5 * i),
            1 + i * 0.00001,
            1.001 + i * 0.00001,
            0.999 + i * 0.00001,
            1 + i * 0.00001,
            10,
            5,
            0,
        )
        for i in range(120)
    ]


def test_indexed_decisions_match_compatibility_evaluation() -> None:
    strategy = load_volatility_expansion(Path("configs/strategies/volatility_expansion.toml"))
    data = bars()
    context = strategy.prepare(data)
    for index in range(strategy.minimum_bars, len(data)):
        assert strategy.evaluate_at("EURUSDm", data, index, 0.00001, context) == strategy.evaluate(
            "EURUSDm", data[: index + 1], 0.00001
        )


def test_diagnostics_exposes_filter_funnel() -> None:
    strategy = load_volatility_expansion(Path("configs/strategies/volatility_expansion.toml"))
    report = collect_diagnostics(strategy, "EURUSDm", bars(), 0.00001)
    assert report.bars_evaluated == 40
    assert report.funnel_counts["bars_evaluated"] == 40
    assert report.funnel_counts["actionable"] == report.actionable_signals
    assert report.funnel_percentages["bars_evaluated"] == 100.0
    values = list(report.funnel_counts.values())
    assert values == sorted(values, reverse=True)


def test_indexed_evaluation_rejects_wrong_context() -> None:
    strategy = load_volatility_expansion(Path("configs/strategies/volatility_expansion.toml"))
    with pytest.raises(TypeError, match="ExpansionContext"):
        strategy.evaluate_at("EURUSDm", bars(), 80, 0.00001, object())


def test_stage_ordered_funnel_matches_observed_reason_profile() -> None:
    from grandmaster_fx.experiments.diagnostics import _ordered_funnel

    counts, percentages = _ordered_funnel(
        9920,
        1,
        {
            "outside_session": 4185,
            "compression_not_confirmed": 4972,
            "expansion_not_confirmed": 762,
            "buy_expansion_confirmed": 1,
        },
    )
    assert counts["session_eligible"] == 5735
    assert counts["spread_eligible"] == 5735
    assert counts["volatility_eligible"] == 5735
    assert counts["compression_eligible"] == 763
    assert counts["expansion_eligible"] == 1
    assert counts["breakout_eligible"] == 1
    assert counts["trend_eligible"] == 1
    assert counts["actionable"] == 1
    assert percentages["actionable"] == 1 / 9920 * 100
