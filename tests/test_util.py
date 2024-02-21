# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import pytest
from formatbreaker.util import validate_address_or_length, uptobyte, downtobyte


def test_uptobyte():
    assert uptobyte(0) == 0
    assert uptobyte(1) == 1
    assert uptobyte(8) == 1
    assert uptobyte(9) == 2


def test_downtobyte():
    assert downtobyte(0) == 0
    assert downtobyte(1) == 0
    assert downtobyte(7) == 0
    assert downtobyte(8) == 1


def test_validate_address_or_length():
    validate_address_or_length(1)
    validate_address_or_length(1, 0)
    validate_address_or_length(0, 0)
    with pytest.raises(IndexError):
        validate_address_or_length(-1, 0)
    validate_address_or_length(5, 0, 5)
    with pytest.raises(IndexError):
        validate_address_or_length(5, 0, 4)
    with pytest.raises(TypeError):
        validate_address_or_length("5")
