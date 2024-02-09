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
        data_source: bytes | BitwiseBytes,
        start_bit: int = 0,
        stop_bit: int | None = None,
    ) -> None:
        """Constructs a BitwiseBytes object

        Parameters
        ----------
        data_source : bytes | BitwiseBytes
            The object to create the new BitwiseBytes object from
        start_bit : int, default 0
            The address of the first bit in `data_source` to be included
        bit_length : int | None, optional
            The address of the first bit in `data_source` to be excluded

        """
        if isinstance(data_source, BitwiseBytes):
            data_length = data_source.length
            self.data = data_source.data
            self.start_bit = data_source.start_bit
            self.start_byte = data_source.start_byte
            self.stop_bit = data_source.start_bit
            self.stop_byte = data_source.start_byte
        elif isinstance(data_source, bytes):
            data_length = len(data_source) * 8
            self.data = data_source
            self.start_bit = 0
            self.start_byte = 0
            self.stop_bit = 0
            self.stop_byte = 0
        else:
            raise TypeError

        validate_address_or_length(start_bit, 0, data_length)
        if stop_bit is not None:
            validate_address_or_length(stop_bit, 0, data_length)
        else:
            stop_bit = data_length

        self.length = stop_bit - start_bit

        self.start_byte = self.start_byte + (self.start_bit + start_bit) // 8
        self.start_bit = (self.start_bit + start_bit) % 8
        self.stop_byte = self.stop_byte + (self.stop_bit + stop_bit) // 8
        self.stop_bit = (self.stop_bit + stop_bit) % 8

    @overload
    def __getitem__(self, item: int) -> bool: ...

    @overload
    def __getitem__(self, item: slice) -> BitwiseBytes: ...

    def __getitem__(self, item: int | slice) -> BitwiseBytes | bool:
        """Returns a value for obj[addr] or obj[slice]

        Parameters
        ----------
        item : int | slice
            The location in the bits to be returned

        Returns
        -------
        BitwiseBytes | bool
            Boolean value of a single bit or a new BitwiseBytes for a slice
        """
        if isinstance(item, slice):
            start, stop, step = item.indices(self.length)
            length = stop - start
            assert length >= 0
            if step != 1:
                raise NotImplementedError

            return BitwiseBytes(self.data, start, stop)

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
        """Returns the length

        Returns
        -------
        int
            Length in bits
        """
        return self.length

    def __bytes__(self) -> bytes:
        """Returns the contained bits as bytes

        Returns
        -------
        bytes
            A right justified copy of the contents
        """
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
        """Converts to a list of booleans

        Returns
        -------
        list[bool]
            A list of the boolean values of the bits
        """
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
    address: Any, amin: int = 0, amax: int | None = None
) -> None:
    """Ensure that a value is a valid address

    Parameters
    ----------
    address : int
        The address to be validated
    amin : int, default 0
        The minimum valid value for `address`
    amax : int | None, optional
        The maximum valid value for `address`, if defined

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


def uniquify_label(label: str, context: dict[str, Any]) -> str:
    """Makes a string key unique in a dictionary by adding a numeric suffix

    Makes a copy of `str`, optionally with " [N]" added where N is the first
    natural number that forms an unused key in `context`

    Parameters
    ----------
    label : str
        A string to be made unique
    context : dict[str, Any]
        An existing dictionary

    Returns
    -------
    str
        A string key that is unused in `context`
    """
    new_label = label
    i = 1
    while new_label in context:
        new_label = label + " " + str(i)
        i = i + 1
    return new_label


def spacer(
    data: bytes | BitwiseBytes,
    context: dict[str, Any],
    start_addr: int,
    stop_addr: int,
) -> int:
    """Reads a spacer into a context dictionary

    Parameters
    ----------
    data : bytes | BitwiseBytes
        Data to be parsed
    context : dict[str, Any]
        Where the results are stored
    start_addr : int
        The address of the first bit or byte in `data_source` to be included
    stop_addr : int
        The address of the first bit or byte in `data_source` to be excluded

    Returns
    -------
    int
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

    spacer_label = uniquify_label(spacer_label, context)
    context[spacer_label] = bytes(data[start_addr:stop_addr])

    return stop_addr
