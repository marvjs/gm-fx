"""Precomputed immutable indicator context for indexed research evaluation."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ExpansionContext:
    """Indicator arrays calculated once for one chronological candle set."""

    close: np.ndarray
    high: np.ndarray
    low: np.ndarray
    atr: np.ndarray
    trend: np.ndarray
    compression_median: np.ndarray
    previous_upper: np.ndarray
    previous_lower: np.ndarray
