"""Dynamic risk and position sizing engine."""

from grandmaster_fx.config.risk import RiskSettings
from grandmaster_fx.domain.mt5 import AccountSnapshot
from grandmaster_fx.domain.symbols import SymbolSnapshot
from grandmaster_fx.execution.models import CloseReason


class RiskManager:
    def __init__(self, settings: RiskSettings) -> None:
        self.settings = settings

    def check_circuit_breakers(
        self,
        account: AccountSnapshot,
        day_start_balance: float,
        floating_profit: float,
    ) -> CloseReason | None:
        """Evaluate if the account has breached global loss thresholds."""
        daily_loss_cash = day_start_balance * (
            self.settings.risk.maximum_daily_loss_percent / 100.0
        )
        if account.equity <= day_start_balance - daily_loss_cash:
            return CloseReason.EMERGENCY_STOP

        floating_loss_cash = account.balance * (
            self.settings.risk.maximum_floating_loss_percent / 100.0
        )
        if floating_profit <= -floating_loss_cash:
            return CloseReason.FLOATING_LOSS_LIMIT

        return None

    def calculate_volume(
        self,
        balance: float,
        entry: float,
        stop_loss: float,
        symbol: SymbolSnapshot,
    ) -> float:
        """Calculate normalized lot size risking exactly the configured percentage."""
        distance = abs(entry - stop_loss)
        if distance <= 0:
            message = "stop loss distance must be positive"
            raise ValueError(message)

        ticks_lost = distance / symbol.tick_size
        loss_per_lot = ticks_lost * symbol.tick_value

        if loss_per_lot <= 0:
            message = "calculated loss per lot must be positive"
            raise ValueError(message)

        risk_cash = balance * (self.settings.risk.risk_per_trade_percent / 100.0)
        raw_volume = risk_cash / loss_per_lot

        return symbol.normalize_volume(raw_volume)
