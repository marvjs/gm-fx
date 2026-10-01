"""Demo dashboard rendering tests."""

from datetime import UTC, datetime

from rich.console import Console

from grandmaster_fx.execution.dashboard import render_dashboard


def test_dashboard_renders_summary_predictions_and_positions() -> None:
    payload: dict[str, object] = {
        "balance": 500.0,
        "equity": 499.5,
        "margin": 20.0,
        "opened": ["USDJPYm"],
        "closed": [],
        "stop_requested": False,
        "predictions": [
            {
                "symbol": "USDJPYm",
                "regime": "trend",
                "signal": "BUY",
                "strategy_allowed": True,
                "confirmation": True,
                "confirmation_reason": "confirmed",
                "duplicate": False,
                "accepted": True,
            }
        ],
        "positions": [
            {
                "ticket": 7,
                "symbol": "USDJPYm",
                "signal": "BUY",
                "volume": 0.01,
                "profit": -0.5,
                "price_open": 157.1,
                "price_current": 157.0,
            }
        ],
    }
    console = Console(record=True, width=140)
    console.print(
        render_dashboard(
            payload,
            strategy="momentum_continuation",
            timeframe="M5",
            cycle_number=3,
            started_at=datetime.now(UTC),
        )
    )
    output = console.export_text()
    assert "Grandmaster FX Demo Dashboard" in output
    assert "USDJPYm" in output
    assert "ACCEPT" in output
    assert "Open Positions" in output
