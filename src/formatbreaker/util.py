"""The module contains utility functions for the package"""


def validate_address_or_length(
    addr: int, amin: int = 0, amax: int | None = None
) -> None:
    """Ensure that a value is a valid address or length

    Args:
        addr: The address to be validated
        amin: The minimum valid value for `addr`
        amax: The maximum valid value for `addr`, if defined

    Raises:
        TypeError: `addr` is not int type
        IndexError: `addr` is not in [`min`, `max`]
    """
    if not isinstance(addr, int):  # type: ignore
        raise TypeError
    if addr < amin:
        raise IndexError
    if amax is not None:
        if addr > amax:
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
