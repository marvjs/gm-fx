"""Restart-safe atomic paper state storage."""

import json
from pathlib import Path

from grandmaster_fx.paper.models import PaperPosition, PaperState


class PaperStateStore:
    def __init__(self, path: Path = Path("data/paper/state.json")) -> None:
        self.path = path

    def load(self, initial_balance: float) -> PaperState:
        if not self.path.is_file():
            return PaperState(balance=initial_balance)
        values = json.loads(self.path.read_text(encoding="utf-8"))
        values["positions"] = [
            PaperPosition.from_dict(item) for item in values.get("positions", [])
        ]
        return PaperState(**values)

    def save(self, state: PaperState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        values = {
            "balance": state.balance,
            "realized_profit": state.realized_profit,
            "positions": [item.to_dict() for item in state.positions],
            "cooldowns": state.cooldowns,
            "updated_at": state.updated_at,
        }
        temporary.write_text(json.dumps(values, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)
