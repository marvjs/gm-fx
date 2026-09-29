"""Deterministic trading strategy framework."""

from grandmaster_fx.strategies.baseline import evaluate_baseline
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision

__all__ = ["DecisionReason", "Signal", "StrategyDecision", "evaluate_baseline"]
