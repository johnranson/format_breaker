"""Code that is mostly used internally"""

from __future__ import annotations
from typing import overload
import operator as op
import formatbreaker.util as fbu


class BitwiseBytes:
    """Allows treating bytes as a subscriptable bit list"""

    _data: bytes
    _start_bit: int
    _stop_bit: int
    _start_byte: int
    _stop_byte: int
    _length: int

    def __init__(
        self,
        source: bytes | BitwiseBytes,
        start_bit: int = 0,
        stop_bit: int | None = None,
    ) -> None:
        """Constructs a BitewiseBytes object

        Args:
            source:The object to create the new BitewiseBytes object from
            start_bit: The address of the first bit in `source` to be included
            bit_length: The address of the first bit in `source` to be excluded
        """
        if isinstance(source, BitwiseBytes):
            self._data = source._data
            base_bit = source._start_bit
            base_byte = source._start_byte
        elif isinstance(source, bytes):  # type: ignore
            self._data = source
            base_bit = 0
            base_byte = 0
        else:
            raise TypeError

        data_length = bitlen(source)

        fbu.validate_address_or_length(start_bit, 0, data_length)
        if stop_bit is not None:
            fbu.validate_address_or_length(stop_bit, 0, data_length)
        else:
            stop_bit = data_length

        self._length = stop_bit - start_bit

        self._start_byte = base_byte + (base_bit + start_bit) // 8
        self._start_bit = (base_bit + start_bit) % 8
        self._stop_byte = base_byte + (base_bit + stop_bit) // 8
        self._stop_bit = (base_bit + stop_bit) % 8

    @overload
    def __getitem__(self, item: int) -> bool: ...
    @overload
    def __getitem__(self, item: slice) -> BitwiseBytes: ...

    def __getitem__(self, item: int | slice) -> BitwiseBytes | bool:
        """Returns a value for obj[addr] or obj[slice]

        Args:
            item: The location in the bits to be returned

        Returns:
            Boolean value of a single bit or a new BitewiseBytes for a slice
        """
        if isinstance(item, slice):
            start, stop, step = item.indices(self._length)
            length = stop - start
            assert length >= 0
            if step != 1:
                raise NotImplementedError

            return BitwiseBytes(self._data, start, stop)

        elif isinstance(item, int):  # type: ignore
            if item >= self._length or item < -self._length:
                raise IndexError
            item = item % self._length
            bit_ind = (self._start_bit + item % 8) % 8
            byte_ind = self._start_byte + (item + self._start_bit) // 8

            bit_raw = (0x80 >> bit_ind) & self._data[byte_ind]

            return bool(bit_raw)

        else:
            raise ValueError

    def __len__(self) -> int:
        """Returns the length

        Returns:
            Length in bits
        """
        return self._length

    def __bytes__(self) -> bytes:
        """Returns the contained bits as bytes

        Returns:
            A right justified copy of the contents
        """
        if self._length == 0:
            return b""

        if self._stop_bit == 0:
            last_byte_addr = self._stop_byte - 1
        else:
            last_byte_addr = self._stop_byte

        single_byte = last_byte_addr == self._start_byte
        multi_byte = last_byte_addr > self._start_byte + 1

        stop_shift = (8 - self._stop_bit) % 8

        if single_byte:
            result = bytes(
                [
                    (self._data[self._start_byte] & (0xFF >> self._start_bit))
                    >> stop_shift
                ]
            )
        else:
            first_byte = bytes(
                [self._data[self._start_byte] & (0xFF >> self._start_bit)]
            )
            last_byte = bytes([self._data[last_byte_addr] & (0xFF << stop_shift)])
            mid_bytes = b""
            if multi_byte:
                mid_bytes = self._data[self._start_byte + 1 : last_byte_addr]

            data = first_byte + mid_bytes + last_byte

            if self._stop_bit == 0:
                result = data
            else:
                shift_data = [b << (8 - stop_shift) for b in data]

                first_part = [b & 0xFF for b in shift_data[:-1]]
                second_part = [b >> 8 for b in shift_data[1:]]

                result = bytes(map(op.add, first_part, second_part))
        return result

    def to_bools(self) -> list[bool]:
        """Converts to a list of booleans

        Returns:
            A list of the boolean values of the bits
        """
        return [bool(self[i]) for i in range(self._length)]

    def __index__(self) -> int:
        if self._length == 0:
            raise RuntimeError
        return int.from_bytes(bytes(self), "big", signed=False)

    def __eq__(self: BitwiseBytes, other: object) -> bool:
        return (
            isinstance(other, BitwiseBytes)
            and (self._length == other._length)
            and (self._length == 0 or (int(self) == int(other)))
        )


def bitlen(obj: bytes | BitwiseBytes) -> int:
    """Returns the length of an object in bits

    Args:
        obj: An object that defines .len()

    Returns:
        The length of `obj` in bits
    """
    if isinstance(obj, bytes):
        return len(obj) * 8
    if isinstance(obj, BitwiseBytes):  # type: ignore
        return len(obj)
    raise NotImplementedError
