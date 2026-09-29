"""Chronological holdout and anchored walk-forward splitting."""

from grandmaster_fx.domain.market_data import Bar

MINIMUM_HOLDOUT_FRACTION = 0.5
MAXIMUM_HOLDOUT_FRACTION = 0.9
MINIMUM_PARTITION_BARS = 2


def holdout_split(bars: list[Bar], fraction: float) -> tuple[list[Bar], list[Bar]]:
    """Split bars chronologically without shuffling."""
    if not MINIMUM_HOLDOUT_FRACTION < fraction < MAXIMUM_HOLDOUT_FRACTION:
        message = "holdout fraction must be between 0.5 and 0.9"
        raise ValueError(message)
    boundary = int(len(bars) * fraction)
    if boundary < MINIMUM_PARTITION_BARS or len(bars) - boundary < MINIMUM_PARTITION_BARS:
        message = "holdout split requires at least two bars in each partition"
        raise ValueError(message)
    return bars[:boundary], bars[boundary:]


def anchored_windows(
    size: int, folds: int, minimum_train: int, minimum_test: int
) -> tuple[tuple[int, int, int, int], ...]:
    """Return expanding training windows and non-overlapping test windows."""
    required = minimum_train + folds * minimum_test
    if size < required:
        message = f"walk-forward validation requires at least {required} bars"
        raise ValueError(message)
    surplus = size - required
    step = minimum_test + surplus // folds
    windows: list[tuple[int, int, int, int]] = []
    train_end = minimum_train
    for fold in range(folds):
        test_start = train_end
        test_end = size if fold == folds - 1 else min(size, test_start + step)
        windows.append((0, train_end, test_start, test_end))
        train_end = test_end
    return tuple(windows)
