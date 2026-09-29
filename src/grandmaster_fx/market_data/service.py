"""Market-data retrieval, conversion, and export."""

import csv
from datetime import UTC, datetime
from pathlib import Path

from grandmaster_fx.domain.market_data import Bar, Tick, Timeframe, validate_bars
from grandmaster_fx.domain.symbols import choose_symbol
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway


class MarketDataService:
    def __init__(self, gateway: Mt5Gateway, allowed: frozenset[str]) -> None:
        self.gateway = gateway
        self.allowed = allowed

    def resolve(self, pair: str) -> str:
        item = choose_symbol(self.gateway.symbols(self.allowed), pair)
        if not item.selected:
            self.gateway.select_symbol(item.name)
        return item.name

    def latest_tick(self, pair: str) -> tuple[str, Tick]:
        name = self.resolve(pair)
        return name, self.gateway.tick(name)

    def bars(
        self, pair: str, timeframe: Timeframe, count: int, *, completed_only: bool = True
    ) -> tuple[str, list[Bar]]:
        if count < 1:
            raise ValueError("count must be positive")
        name = self.resolve(pair)
        start = 1 if completed_only else 0
        return name, validate_bars(self.gateway.bars(name, timeframe, count, start), timeframe)


def export_bars(bars: list[Bar], destination: Path) -> Path:
    if destination.suffix.lower() != ".csv":
        raise ValueError("export extension must be .csv")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "tick_volume",
                "spread",
                "real_volume",
            ],
        )
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "time": bar.time.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "tick_volume": bar.tick_volume,
                    "spread": bar.spread,
                    "real_volume": bar.real_volume,
                }
            )
    return destination


def default_export(pair: str, timeframe: Timeframe, extension: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("data/exports") / f"{pair.upper()}_{timeframe.value}_{stamp}.{extension}"
