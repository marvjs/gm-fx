"""CSV and JSON strategy research artifact exports."""

import csv
import json
from dataclasses import asdict
from pathlib import Path

from grandmaster_fx.research.models import ResearchAnalysis, ValidationReport


def export_research(
    analysis: ResearchAnalysis, validation: ValidationReport, directory: Path
) -> tuple[Path, Path, Path]:
    """Write a trade ledger, summary JSON, and validation JSON."""
    directory.mkdir(parents=True, exist_ok=True)
    symbol = analysis.result.symbol
    ledger = directory / f"{symbol}_trade_ledger.csv"
    summary = directory / f"{symbol}_research_summary.json"
    verdict = directory / f"{symbol}_validation.json"
    fields = [
        "symbol",
        "signal",
        "entry_time",
        "exit_time",
        "entry",
        "exit",
        "volume",
        "gross_pnl",
        "costs",
        "net_pnl",
        "return_r",
        "holding_bars",
        "exit_reason",
    ]
    with ledger.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for trade in analysis.result.trades:
            writer.writerow(
                {
                    "symbol": trade.symbol,
                    "signal": trade.signal.value,
                    "entry_time": trade.entry_time.isoformat(),
                    "exit_time": trade.exit_time.isoformat(),
                    "entry": trade.entry,
                    "exit": trade.exit,
                    "volume": trade.volume,
                    "gross_pnl": trade.gross_pnl,
                    "costs": trade.costs,
                    "net_pnl": trade.net_pnl,
                    "return_r": trade.return_r,
                    "holding_bars": trade.holding_bars,
                    "exit_reason": trade.exit_reason.value,
                }
            )
    summary.write_text(
        json.dumps(
            {
                "symbol": symbol,
                "metrics": asdict(analysis.result.metrics),
                "costs": asdict(analysis.costs),
                "by_signal": [asdict(item) for item in analysis.by_signal],
                "by_exit_reason": [asdict(item) for item in analysis.by_exit_reason],
                "by_hour": [asdict(item) for item in analysis.by_hour],
                "by_weekday": [asdict(item) for item in analysis.by_weekday],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    verdict.write_text(json.dumps(asdict(validation), indent=2), encoding="utf-8")
    return ledger, summary, verdict
