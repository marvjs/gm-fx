"""Regression tests for NumPy-style structured MT5 bar rows."""

from types import SimpleNamespace

import pytest

from grandmaster_fx.exceptions import Mt5DataError
from grandmaster_fx.infrastructure.mt5_gateway import _structured_row_mapping


class Scalar:
    def __init__(self, value: object) -> None:
        self.value = value

    def item(self) -> object:
        return self.value


class StructuredRow:
    dtype = SimpleNamespace(names=("time", "open", "close"))

    def __init__(self) -> None:
        self.values = {"time": Scalar(60), "open": Scalar(1.1), "close": Scalar(1.2)}

    def __getitem__(self, key: str) -> Scalar:
        return self.values[key]


def test_numpy_style_structured_row_is_converted_by_field_name() -> None:
    assert _structured_row_mapping(StructuredRow()) == {
        "time": 60,
        "open": 1.1,
        "close": 1.2,
    }


def test_named_tuple_style_row_is_supported() -> None:
    row = SimpleNamespace(_asdict=lambda: {"time": 60})
    assert _structured_row_mapping(row) == {"time": 60}


def test_unknown_row_type_is_rejected_cleanly() -> None:
    with pytest.raises(Mt5DataError, match="Unsupported MT5 bar row type"):
        _structured_row_mapping(object())
