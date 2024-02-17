"""Code that is mostly used internally"""

from __future__ import annotations
from io import BufferedIOBase, BytesIO
from typing import Any, overload
from operator import add
from collections import ChainMap, deque
from collections.abc import Collection
import bisect
from enum import Enum

AddrType = Enum("AddrType", ["BIT", "BYTE", "BYTE_STRICT", "PARENT"])


class FBError(Exception):
    """This error should be raised when a Parser fails to parse the data
    because it doesn't fit expectations. The idea is that optional data
    types can fail to be parsed, and the top level code will catch the
    exception and try something else.
    """


class FBNoDataError(FBError):
    """This error should be raised when a Parser tries to read past the
    end of the input data."""


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


class Context(ChainMap):
    """Contains the results from parsing in a nested manner, allowing reverting failed
    optional data reads"""

    def __setitem__(self, key: str, value: Any) -> None:
        """Sets the underlying ChainMap value but updates duplicate keys

        Args:
            key: _description_
            value: _description_
        """
        new_key = key
        i = 1
        while new_key in self:
            new_key = key + " " + str(i)
            i = i + 1
        super().__setitem__(new_key, value)

    def update_ext(self) -> None:
        """Loads all of the current Context values into the parent Context"""
        if len(self.maps) == 1:
            raise RuntimeError
        self.maps[1].update(self.maps[0])
        self.maps[0].clear()


DATA_BUFFER_SIZE = 1024 * 8


class DataSource(ChainMap):
    """This class holds a source of data, buffers it, and keeps a nested contexts
    storing address data allowing reversion of failed reads."""

    _source: BufferedIOBase
    _bounds: deque[int]
    _buffers: deque[bytes]
    _source_empty: bool

    @property
    def _cursor(self) -> int:
        return self["_cursor"]

    @_cursor.setter
    def _cursor(self, addr: int) -> None:
        self["_cursor"] = addr

    @property
    def _base(self) -> int:
        return self["_base"]

    @_base.setter
    def _base(self, addr: int) -> None:
        self["_base"] = addr

    @property
    def _addr_type(self) -> AddrType:
        return self["_addr_type"]

    @_addr_type.setter
    def _addr_type(self, t: AddrType) -> None:
        self["_addr_type"] = t

    @property
    def _revertible(self) -> bool:
        return self["_revertible"]

    @_revertible.setter
    def _revertible(self, revertible: bool) -> None:
        self["_revertible"] = revertible

    def __init__(self, *maps, source: bytes | BufferedIOBase | None = None):
        super().__init__(*maps)
        if source is None:
            return

        # Attributes
        self._source = BytesIO(b"")
        self._bounds = deque([0])
        self._buffers = deque()
        self._source_empty = False

        # Stored in the ChainMap
        self._revertible = False
        self._cursor = 0
        self._base = 0
        self._addr_type = AddrType.BYTE

        if isinstance(source, bytes):
            self._buffers.append(source)
            self._bounds.append(bitlen(source))
            self._source_empty = True
        elif isinstance(source, BufferedIOBase):
            self._source = source
            self._read_into_buffer(DATA_BUFFER_SIZE)
        else:
            raise NotImplementedError

    def read(self, length: int | None = None) -> bytes:
        """Reads from the buffer

        Args:
            length: The number of bits or bytes to read based on `AddrType.BYTE`. Reads
            all data available if undefined.

        Returns:
            The requested data, if available. Bits are converted to right justified
            bytes.
        """
        if self._addr_type == AddrType.BYTE:
            return self.read_bytes(length)
        return bytes(self.read_bits(length))

    def read_bytes(self, byte_length: int | None = None) -> bytes:
        """Reads bytes from the buffer

        Args:
            length: The number of bytes to read. Reads all data available if undefined.

        Returns:
            The requested bytes, if available
        """
        if byte_length is not None:
            if byte_length == 0:
                return b""
            return bytes(self.read_bits(bit_length=byte_length * 8))
        return bytes(self.read_bits())

    def read_bits(self, bit_length: int | None = None) -> BitwiseBytes:
        """Reads bits from the buffer

        Args:
            length: The number of bits to read. Reads all data available if undefined.

        Returns:
            The requested bits, if available
        """
        start_addr = self._cursor

        if start_addr < self.lower_bound():
            raise IndexError("Cursor points to data no longer in buffers")
        if start_addr > self.upper_bound():
            raise IndexError("Cursor points past end of buffered data.")

        if bit_length is not None:
            if bit_length == 0:
                return BitwiseBytes(b"")

            if bit_length < 0:
                raise IndexError("Cannot read negative length.")

            stop_addr = start_addr + bit_length
            if stop_addr > self.upper_bound():
                bits_needed = stop_addr - self.upper_bound()
                if self._read_into_buffer(bits_needed) < bits_needed:
                    raise FBNoDataError
        else:
            if not self._source_empty:
                self._read_into_buffer()
            stop_addr = self._bounds[-1]

        result = self._get_data_from_buffers(start_addr, stop_addr)
        self._cursor = stop_addr
        self.trim()
        return result

    def _get_data_from_buffers(self, start: int, stop: int):
        assert stop > start >= 0

        start_buffer = bisect.bisect_right(self._bounds, start) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self._buffers)

        stop_buffer = bisect.bisect_left(self._bounds, stop) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self._buffers)

        start_buffer_start = start - self._bounds[start_buffer]
        stop_buffer_stop = stop - self._bounds[stop_buffer]

        start_buffer_start = downtobyte(start_buffer_start)
        stop_buffer_stop = uptobyte(stop_buffer_stop)

        if start_buffer == stop_buffer:
            byte_result = self._buffers[start_buffer][
                start_buffer_start:stop_buffer_stop
            ]

        elif start_buffer + 1 == stop_buffer:
            byte_result = (
                self._buffers[start_buffer][start_buffer_start:]
                + self._buffers[stop_buffer][:stop_buffer_stop]
            )
        else:
            byte_result = self._buffers[start_buffer][start_buffer_start:]
            for i in range(start_buffer + 1, stop_buffer):
                byte_result = byte_result + self._buffers[i]
            byte_result = byte_result + self._buffers[stop_buffer][:stop_buffer_stop]

        start_slice = start % 8
        stop_slice = start_slice + stop - start
        result = BitwiseBytes(byte_result, start_slice, stop_slice)
        return result

    def _read_into_buffer(self, bit_length=None) -> int:
        """Reads bytes from the underlying source into a buffer

        Args:
            bit_length: The minimum number of bits to read into the buffer. Reads all
            available data if undefined

        Raises:
            FBNoDataError: Raised if we have already hit EOF.

        Returns:
            Returns the number of bytes read.
        """
        if self._source_empty:
            raise FBNoDataError
        if bit_length is not None:
            byte_length = uptobyte(max(DATA_BUFFER_SIZE, bit_length))
            read_length = byte_length * 8
            data = self._source.read(byte_length)
        else:
            read_length = float("inf")
            data = self._source.read()
            self._source_empty = True
        data_length = bitlen(data)
        self._source_empty = data_length < read_length
        self._bounds.append(self._bounds[-1] + data_length)
        self._buffers.append(data)
        return data_length

    def trim(self) -> None:
        """Discard any buffers that have been read and are unneeded"""
        assert self._cursor <= self._bounds[-1]
        # This would imply that the cursor points to data we haven't read

        assert len(self._bounds) > 1
        # This would imply that we have have no buffers

        if self._revertible:
            return

        while self._cursor > self._bounds[1]:
            del self._buffers[0]
            del self._bounds[0]

    def make_child(
        self,
        relative: bool = True,
        addr_type: AddrType = AddrType.PARENT,
        revertible: bool = False,
    ) -> DataSource:
        """Creates a child DataSource with its own cursor and addressing

        Args:
            relative: Whether the addressing is relative to cursor location on creation
            addr_type: Whether the addressing is bitwise or bytewise
            revertible: Whether the reads to this DataSource and its children can fail
            and be reverted
        Returns:
            The child DataSource
        """
        child: DataSource = super().new_child()
        child._source = self._source
        child._buffers = self._buffers
        child._bounds = self._bounds
        child._source_empty = self._source_empty
        if relative:
            child._base = self._cursor
        match addr_type:
            case AddrType.PARENT:
                pass
            case AddrType.BYTE:
                child._addr_type = AddrType.BYTE
            case AddrType.BYTE_STRICT:
                child._addr_type = AddrType.BYTE
                if self._cursor % 8:
                    raise FBError("Strict byte addr_type must start on a byte boundary")
            case AddrType.BIT:
                child._addr_type = AddrType.BIT
        if self._addr_type != addr_type and not relative:
            raise RuntimeError("Address type changes must use relative addr_type")
        if revertible:
            child._revertible = True
        return child

    def current_address(self) -> int:
        """Returns the current address

        Returns:
            The current read address, bitwise or bytewise according to `self.addr_type`
        """
        if self._addr_type == AddrType.BYTE:
            return (self._cursor - self._base) // 8
        return self._cursor - self._base

    def __enter__(self) -> DataSource:
        return self

    def __exit__(self, e_type, value, traceback) -> bool:
        if e_type is None:
            # Data has been read successfully and we update the parent DataSource with
            # the current cursor location before this Cursor is discarded.
            self._update_parent()
            return True
        if e_type is FBError:
            if self.maps[0]["_revertible"]:
                # In the case that the current data read is revertible, upon an FBError,
                # we don't update the parent DataSource cursor, essentially undoing all
                # data reads with this DataSource
                return True
        raise

    def _update_parent(self) -> None:
        """Updates the parent DataSource with the current cursor location.

        Raises:
            RuntimeError: Returned if the parent is bytewise and the current cursor is
            not on a byte address
        """
        parent = self.parents
        if parent:
            if parent._addr_type == AddrType.BYTE and (self._cursor - self._base) % 8:
                raise RuntimeError("Cannot return non-byte length to bytewise parent")
            parent._cursor = self._cursor

    def lower_bound(self) -> int:
        """Returns the bit address of the first byte in the buffers

        Returns:
            The bit address of the first byte in the buffers
        """
        return self._bounds[0]

    def upper_bound(self) -> int:
        """Returns the bit address after the last byte in the buffers

        Returns:
            The bit address after the last byte in the buffers
        """
        return self._bounds[-1]


def bitlen(obj: Collection) -> int:
    """Returns the length of an object in bits

    Args:
        obj: An object that defines .len()

    Returns:
        The length of `obj` in bits
    """
    return len(obj) * 8


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


def spacer(
    data: DataSource,
    context: Context,
    stop_addr: int,
):
    """Reads a spacer into a context dictionary

    Args:
        data: Data being parsed
        context: Where results are stored
        stop_addr: The address of the first bit or byte in `data_source` to be excluded

    """
    start_addr = data.current_address()
    length = stop_addr - start_addr

    if length == 0:
        return
    if length > 1:
        spacer_label = "spacer_" + hex(start_addr) + "-" + hex(stop_addr - 1)
    else:
        spacer_label = "spacer_" + hex(start_addr)

    context[spacer_label] = data.read(length)
