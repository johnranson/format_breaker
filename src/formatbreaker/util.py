"""Code that is mostly used internally"""

from __future__ import annotations
from typing import Any, overload
from operator import add
from collections.abc import MutableMapping


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
        data_source: bytes | BitwiseBytes,
        start_bit: int = 0,
        stop_bit: int | None = None,
    ) -> None:
        """Constructs a BitwiseBytes object

        Args:
            data_source:The object to create the new BitwiseBytes object from
            start_bit: The address of the first bit in `data_source` to be included
            bit_length: The address of the first bit in `data_source` to be excluded

        """
        if isinstance(data_source, BitwiseBytes):
            data_length = data_source._length
            self._data = data_source._data
            base_bit = data_source._start_bit
            base_byte = data_source._start_byte
        elif isinstance(data_source, bytes):
            data_length = len(data_source) * 8
            self._data = data_source
            base_bit = 0
            base_byte = 0
        else:
            raise TypeError

        validate_address_or_length(start_bit, 0, data_length)
        if stop_bit is not None:
            validate_address_or_length(stop_bit, 0, data_length)
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
            Boolean value of a single bit or a new BitwiseBytes for a slice
        """
        if isinstance(item, slice):
            start, stop, step = item.indices(self._length)
            length = stop - start
            assert length >= 0
            if step != 1:
                raise NotImplementedError

            return BitwiseBytes(self._data, start, stop)

        elif isinstance(item, int):
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

                result = bytes(map(add, first_part, second_part))
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


def validate_address_or_length(
    address: Any, amin: int = 0, amax: int | None = None
) -> None:
    """Ensure that a value is a valid address

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


def spacer(
    data: bytes | BitwiseBytes,
    context: Context,
    start_addr: int,
    stop_addr: int,
) -> int:
    """Reads a spacer into a context dictionary

    Args:
        data: Data being parsed
        context: Where results are stored including prior results in the same
            containing Block
        start_addr: The address of the first bit or byte in `data_source` to be included
        stop_addr: The address of the first bit or byte in `data_source` to be excluded

    Returns:
        The address of the first bit or byte in `data_source` after the spacer
    """

    print(start_addr, stop_addr, len(data))

    validate_address_or_length(start_addr, 0, len(data))
    validate_address_or_length(stop_addr, start_addr, len(data))

    if stop_addr == start_addr:
        return stop_addr

    if stop_addr > 1 + start_addr:
        spacer_label = "spacer_" + hex(start_addr) + "-" + hex(stop_addr - 1)
    else:
        spacer_label = "spacer_" + hex(start_addr)

    context[spacer_label] = bytes(data[start_addr:stop_addr])

    return stop_addr


class Context(MutableMapping):
    __local_context: dict
    __ext_context: dict | Context

    def __init__(
        self,
        ext_context: Context | dict | None = None,
        *,
        local_context: dict | None = None,
    ):
        if local_context is not None:
            self.__local_context = local_context
        else:
            self.__local_context = {}
        if ext_context is not None:
            self.__ext_context = ext_context
        else:
            self.__ext_context = {}

    def __getitem__(self, key):
        if key in self.__local_context:
            return self.__local_context[key]
        return self.__ext_context[key]

    def __setitem__(self, key, value):
        new_key = key
        i = 1
        while new_key in self:
            new_key = key + " " + str(i)
            i = i + 1
        print(new_key)
        self.__local_context[new_key] = value

    def __delitem__(self, key):
        del self.__local_context[key]

    def __len__(self):
        return len(self.__local_context) + len(self.__ext_context)

    def __repr__(self):
        return repr((self.__ext_context, self.__local_context))

    def __iter__(self):
        yield from self.__ext_context
        yield from self.__local_context

    def clear(self):
        self.__local_context = {}

    def copy(self):
        return Context(self.__ext_context, local_context=self.__local_context.copy())

    def update_ext(self):
        self.__ext_context.update(self.__local_context)
        self.__local_context.clear()
