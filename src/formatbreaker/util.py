"""The module contains utility functions for the package"""

from __future__ import annotations
from typing import Any


def validate_address_or_length(
    address: Any, amin: int = 0, amax: int | None = None
) -> None:
    """Ensure that a value is a valid address or length

    Args:
        address: The address to be validated
        amin: The minimum valid value for `address`
        amax: The maximum valid value for `address`, if defined

    Raises:
        TypeError: `address` is not int type
        IndexError: `address` is not in [`min`, `max`]
    """
    if not isinstance(address, int):
        raise TypeError
    if address < amin:
        raise IndexError
    if amax is not None:
        if address > amax:
            raise IndexError


def uptobyte(bits: int) -> int:
    """Converts a bit length to the number of whole bytes needed to contain it

    Args:
        bits: A bit length or address

    Returns:
        The number of whole bytes needed to contain the `bits`
    """
    return -(bits // -8)


def downtobyte(bits: int) -> int:
    """Converts a bit length or address to the number of whole bytes included

    Args:
        bits: A bit length or address

    Returns:
        The number of whole bytes included `bits`
    """
    return bits // 8
