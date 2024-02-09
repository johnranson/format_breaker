"""Code that is mostly used internally"""

from __future__ import annotations
from typing import Any, overload
from operator import add


class BitwiseBytes:
    """Allows treating bytes as a subscriptable bit list"""

    data: bytes
    start_bit: int
    stop_bit: int
    start_byte: int
    stop_byte: int
    length: int

    def __init__(
        self,
        value: bytes | BitwiseBytes,
        start_byte: int = 0,
        start_bit: int = 0,
        length: int | None = None,
    ) -> None:
        if isinstance(value, BitwiseBytes):
            if (length is not None) or (start_bit > 0) or (start_byte > 0):
                raise ValueError
            self.data = value.data
            self.start_byte = value.start_byte
            self.start_bit = value.start_bit
            self.stop_byte = value.stop_byte
            self.stop_bit = value.stop_bit
            self.length = value.length
        elif isinstance(value, bytes):
            self.data = value

            if not isinstance(start_byte, int):
                raise ValueError
            if not isinstance(start_bit, int):
                raise ValueError
            if not (isinstance(length, int) or length is None):
                raise ValueError

            if start_byte > 0 and start_bit > 7:
                raise IndexError
            if start_byte < 0 or start_bit < 0:
                raise IndexError

            self.start_byte = start_byte + start_bit // 8
            self.start_bit = start_bit % 8

            if length is not None:
                if length < 0:
                    raise IndexError
                self.length = length
            else:
                self.length = (
                    len(value) * 8 - self.start_bit - self.start_byte * 8
                )

            last_bit = self.start_bit + self.start_byte * 8 + self.length

            if last_bit > len(value) * 8:
                raise IndexError

            self.stop_bit = self.length + self.start_bit
            self.stop_byte = self.stop_bit // 8 + self.start_byte
            self.stop_bit = self.stop_bit % 8
        else:
            raise ValueError

    @overload
    def __getitem__(self, item: int) -> bool: ...

    @overload
    def __getitem__(self, item: slice) -> BitwiseBytes: ...

    def __getitem__(self, item: int | slice) -> BitwiseBytes | bool:
        if isinstance(item, slice):
            start, stop, step = item.indices(self.length)
            length = stop - start
            assert length >= 0
            if step != 1:
                raise NotImplementedError
            start_bit = (self.start_bit + start) % 8
            start_byte = self.start_byte + (start + self.start_bit) // 8

            return BitwiseBytes(self.data, start_byte, start_bit, length)

        elif isinstance(item, int):
            if item >= self.length or item < -self.length:
                raise IndexError
            item = item % self.length
            bit_ind = (self.start_bit + item % 8) % 8
            byte_ind = self.start_byte + (item + self.start_bit) // 8

            bit_raw = (0x80 >> bit_ind) & self.data[byte_ind]

            return bool(bit_raw)

        else:
            raise ValueError

    def __len__(self) -> int:
        return self.length

    def __bytes__(self) -> bytes:
        if self.length == 0:
            return b""

        if self.stop_bit == 0:
            last_byte_addr = self.stop_byte - 1
        else:
            last_byte_addr = self.stop_byte

        single_byte = last_byte_addr == self.start_byte
        multi_byte = last_byte_addr > self.start_byte + 1

        stop_shift = (8 - self.stop_bit) % 8

        if single_byte:
            result = bytes(
                [
                    (self.data[self.start_byte] & (0xFF >> self.start_bit))
                    >> stop_shift
                ]
            )
        else:
            first_byte = bytes(
                [self.data[self.start_byte] & (0xFF >> self.start_bit)]
            )
            last_byte = bytes(
                [self.data[last_byte_addr] & (0xFF << stop_shift)]
            )
            mid_bytes = b""
            if multi_byte:
                mid_bytes = self.data[self.start_byte + 1 : last_byte_addr]

            data = first_byte + mid_bytes + last_byte

            if self.stop_bit == 0:
                result = data
            else:
                shift_data = [b << (8 - stop_shift) for b in data]

                first_part = [b & 0xFF for b in shift_data[:-1]]
                second_part = [b >> 8 for b in shift_data[1:]]

                result = bytes(map(add, first_part, second_part))
        return result

    def to_bools(self) -> list[bool]:
        return [bool(self[i]) for i in range(self.length)]

    def __index__(self) -> int:
        if self.length == 0:
            raise RuntimeError
        return int.from_bytes(bytes(self), "big", signed=False)

    def __eq__(self: BitwiseBytes, other: object) -> bool:
        return (
            isinstance(other, BitwiseBytes)
            and (self.length == other.length)
            and (self.length == 0 or (int(self) == int(other)))
        )


def validate_address_or_length(
    address: int, amin: int = 0, amax: int | None = None
) -> None:
    """_summary_

    Parameters
    ----------
    address : int
        The address to be validated
    amin : int, default 0
        The minimum valid value for `address`
    amax : int | None, optional
        The maximum valid value for `address` if defined

    Raises
    ------
    TypeError
        `address` is not int type
    IndexError
        `address` is not in [`min`, `max`]
    """
    if not isinstance(address, int):
        raise TypeError
    if address < amin:
        raise IndexError
    if amax is not None:
        if address > amax:
            raise IndexError


def uniquify_name(name: str, context: dict[str, Any]) -> str:
    """This adds " N" to a string key if the key already exists in the
        dictionary, where N is the first natural number that makes the
        key unique

    Args:
        name (string): A string
        context (dictionary): Any dictionary

    Returns:
        string: A unique string key
    """
    new_name = name
    i = 1
    while new_name in context:
        new_name = name + " " + str(i)
        i = i + 1
    return new_name


def spacer(
    data: bytes | BitwiseBytes,
    context: dict[str, Any],
    addr: int,
    spacer_size: int,
) -> int:
    """Reads a spacer of a certain length from the data, and saves it
        to the context dictionary

    Args:
        data (bytes or BitwiseBytes): Data being parsed
        context (dict): The dictionary where results are stored
        abs_addr (int): The current absolute bit or byte address in the data
        spacer_size (_type_): The size in bits or bytes of the spacer

    Returns:
        abs_addr (int): The bit or byte address following the spacer
    """
    end_addr = addr + spacer_size

    if addr < 0:
        raise IndexError
    if end_addr > len(data):
        raise IndexError
    if spacer_size == 0:
        return end_addr
    if spacer_size < 0:
        raise ValueError
    if spacer_size > 1:
        spacer_name = "spacer_" + hex(addr) + "-" + hex(addr + spacer_size - 1)
    else:
        spacer_name = "spacer_" + hex(addr)

    spacer_name = uniquify_name(spacer_name, context)

    context[spacer_name] = bytes(data[addr:end_addr])
    return end_addr
