"""Local JSON cache for completed historical candles."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from grandmaster_fx.domain.market_data import Bar, Timeframe

CACHE_DIRECTORY = Path("data/cache/market")


def cache_path(symbol: str, timeframe: Timeframe, count: int) -> Path:
    """Return the deterministic path for one candle request."""
    safe_symbol = "".join(character for character in symbol if character.isalnum())
    return CACHE_DIRECTORY / f"{safe_symbol}_{timeframe.value}_{count}.json"


def save_bars(symbol: str, timeframe: Timeframe, count: int, bars: list[Bar]) -> Path:
    """Store completed candles locally for repeatable research runs."""
    path = cache_path(symbol, timeframe, count)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for bar in bars:
        item = asdict(bar)
        item["time"] = bar.time.isoformat()
        payload.append(item)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def load_bars(symbol: str, timeframe: Timeframe, count: int) -> list[Bar] | None:
    """Load cached candles when an exact request is available."""
    path = cache_path(symbol, timeframe, count)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        Bar(
            time=datetime.fromisoformat(item["time"]),
            open=item["open"],
            high=item["high"],
            low=item["low"],
            close=item["close"],
            tick_volume=item["tick_volume"],
            spread=item["spread"],
            real_volume=item["real_volume"],
        )
        for item in payload
    ]
