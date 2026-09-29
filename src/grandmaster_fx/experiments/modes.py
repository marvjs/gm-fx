"""Experiment execution modes."""

from enum import StrEnum


class ExperimentMode(StrEnum):
    """Control research depth and runtime."""

    QUICK = "quick"
    HOLDOUT = "holdout"
    FULL = "full"
