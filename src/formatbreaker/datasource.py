"""Code that is mostly used internally"""

from __future__ import annotations
from typing import override
import io
import collections
import bisect
import enum
import formatbreaker.bitwisebytes as bitwisebytes
import formatbreaker.exceptions as fbe
import formatbreaker.util as fbu


AddrType = enum.Enum("AddrType", ["BIT", "BYTE", "BYTE_STRICT", "PARENT"])
DATA_BUFFER_SIZE = 1024 * 8


class DataSource:
    """This class holds a source of data, buffers it, and keeps a nested contexts
    storing address data allowing reversion of failed reads."""

    __slots__ = (
        "__with_safe",
        "__has_child",
        "__revertible",
        "__cursor",
        "__parent",
        "__base",
        "__addr_type",
        "__bounds",
        "__buffers",
        "__source_empty",
        "__source",
    )

    __with_safe: bool
    __has_child: bool
    __revertible: bool | None
    __cursor: int
    __parent: DataSource | None
    __base: int | None
    __addr_type: AddrType | None
    __bounds: collections.deque[int]
    __buffers: collections.deque[bytes]
    __source_empty: bool
    __source: bytes | io.BufferedIOBase

    # Properties - All properties are stored in the current Datasource
    # Local Properties - Stored in the current dictionary

    @property
    def _base(self) -> int:
        if self.__base is not None:
            return self.__base
        assert self.__parent is not None
        return self.__parent._base

    @property
    def _addr_type(self) -> AddrType:
        if self.__addr_type is not None:
            return self.__addr_type
        assert self.__parent is not None
        return self.__parent._addr_type

    @property
    def _revertible(self) -> bool:
        if self.__revertible:
            return True
        if self.__parent is not None:
            return self.__parent._revertible
        return False

    @property
    def _source_empty(self) -> bool:
        return self.__source_empty

    @_source_empty.setter
    def _source_empty(self, source_empty: bool) -> None:
        self.__source_empty = source_empty
        if self.__parent is not None:
            self.__parent._source_empty = source_empty

    @override
    def __init__(
        self,
        src: bytes | io.BufferedIOBase | DataSource,
        relative: bool = True,
        addr_type: AddrType = AddrType.PARENT,
        revertible: bool = False,
    ):
        self.__with_safe = False

        self.__has_child = False

        self.__revertible = revertible

        if isinstance(src, DataSource):

            self.__source = src.__source
            self.__bounds = src.__bounds
            self.__buffers = src.__buffers
            self.__cursor = src.__cursor
            self.__parent = src
            self.__source_empty = src._source_empty
            self.__parent.__has_child = True
            if relative:
                self.__base = self.__cursor
            match addr_type:
                case AddrType.PARENT:
                    self.__addr_type = None
                case AddrType.BYTE:
                    self.__addr_type = AddrType.BYTE
                case AddrType.BYTE_STRICT:
                    self.__addr_type = AddrType.BYTE
                    if src.__cursor % 8:
                        raise fbe.FBError(
                            "Strict byte addr_type must start on a byte boundary"
                        )
                case AddrType.BIT:
                    self.__addr_type = AddrType.BIT
            if src._addr_type != addr_type and not relative:
                raise RuntimeError("Address type changes must use relative addr_type")
        else:
            # No parent
            self.__parent = None  # Must be first
            if addr_type == AddrType.PARENT:
                self.__addr_type = AddrType.BYTE
            else:
                self.__addr_type == addr_type

            self.__source = io.BytesIO(b"")
            self.__bounds = collections.deque([0])
            self.__buffers = collections.deque()
            self._source_empty = False

            self.__cursor = 0
            self.__base = 0
            if isinstance(src, bytes):
                self.__buffers.append(src)
                self.__bounds.append(bitwisebytes.bitlen(src))
                self._source_empty = True
            elif isinstance(src, io.BufferedIOBase):
                self.__source = src
                self._read_into_buffer(DATA_BUFFER_SIZE)
            else:
                raise NotImplementedError

    def fail_if_unsafe(self) -> None:
        if self.__has_child:
            raise RuntimeError("Attemped to access a DataSource with a child.")
        if not self.__with_safe:
            raise RuntimeError("Datasource used outside a with statement.")

    def read(self, length: int | None = None) -> bytes:
        """Reads from the buffer

        Args:
            length: The number of bits or bytes to read based on `AddrType.BYTE`. Reads
            all data available if undefined.

        Returns:
            The requested data, if available. Bits are converted to right justified
            bytes.
        """
        self.fail_if_unsafe()

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
        self.fail_if_unsafe()
        if byte_length is not None:
            if byte_length == 0:
                return b""
            return bytes(self.read_bits(bit_length=byte_length * 8))
        return bytes(self.read_bits())

    def read_bits(self, bit_length: int | None = None) -> bitwisebytes.BitwiseBytes:
        """Reads bits from the buffer

        Args:
            length: The number of bits to read. Reads all data available if undefined.

        Returns:
            The requested bits, if available
        """
        self.fail_if_unsafe()
        start_addr = self.__cursor

        if start_addr < self.lower_bound():
            raise IndexError("Cursor points to data no longer in buffers")
        if start_addr > self.upper_bound():
            raise IndexError("Cursor points past end of buffered data.")

        if bit_length is not None:
            if bit_length == 0:
                return bitwisebytes.BitwiseBytes(b"")

            if bit_length < 0:
                raise IndexError("Cannot read negative length.")

            stop_addr = start_addr + bit_length
            if stop_addr > self.upper_bound():
                bits_needed = stop_addr - self.upper_bound()
                if self._read_into_buffer(bits_needed) < bits_needed:
                    raise fbe.FBNoDataError
        else:
            if not self._source_empty:
                self._read_into_buffer()
            stop_addr = self.__bounds[-1]

        result = self._get_data_from_buffers(start_addr, stop_addr)
        self.__cursor = stop_addr
        self.trim()
        return result

    def _get_data_from_buffers(self, start: int, stop: int):
        assert stop > start >= 0

        start_buffer = bisect.bisect_right(self.__bounds, start) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self.__buffers)

        stop_buffer = bisect.bisect_left(self.__bounds, stop) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self.__buffers)

        start_buffer_start = start - self.__bounds[start_buffer]
        stop_buffer_stop = stop - self.__bounds[stop_buffer]

        start_buffer_start = fbu.downtobyte(start_buffer_start)
        stop_buffer_stop = fbu.uptobyte(stop_buffer_stop)

        if start_buffer == stop_buffer:
            byte_result = self.__buffers[start_buffer][
                start_buffer_start:stop_buffer_stop
            ]

        elif start_buffer + 1 == stop_buffer:
            byte_result = (
                self.__buffers[start_buffer][start_buffer_start:]
                + self.__buffers[stop_buffer][:stop_buffer_stop]
            )
        else:
            byte_result = self.__buffers[start_buffer][start_buffer_start:]
            for i in range(start_buffer + 1, stop_buffer):
                byte_result = byte_result + self.__buffers[i]
            byte_result = byte_result + self.__buffers[stop_buffer][:stop_buffer_stop]

        start_slice = start % 8
        stop_slice = start_slice + stop - start
        result = bitwisebytes.BitwiseBytes(byte_result, start_slice, stop_slice)
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
            raise fbe.FBNoDataError
        if bit_length is not None:
            byte_length = fbu.uptobyte(max(DATA_BUFFER_SIZE, bit_length))
            read_length = byte_length * 8
            data = self.__source.read(byte_length)
        else:
            read_length = float("inf")
            data = self.__source.read()
            self._source_empty = True
        data_length = bitwisebytes.bitlen(data)
        self._source_empty = data_length < read_length
        self.__bounds.append(self.__bounds[-1] + data_length)
        self.__buffers.append(data)
        return data_length

    def trim(self) -> None:
        """Discard any buffers that have been read and are unneeded"""
        self.fail_if_unsafe()
        assert self.__cursor <= self.__bounds[-1]
        # This would imply that the cursor points to data we haven't read

        assert len(self.__bounds) > 1
        # This would imply that we have have no buffers

        if self._revertible:
            return

        while self.__cursor > self.__bounds[1]:
            del self.__buffers[0]
            del self.__bounds[0]

    def make_child(
        self,
        **kwargs,
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
        # pylint: disable=protected-access
        self.fail_if_unsafe()
        child: DataSource = self.__class__(self, **kwargs)
        return child

    def current_address(self) -> int:
        """Returns the current address

        Returns:
            The current read address, bitwise or bytewise according to `self.addr_type`
        """
        self.fail_if_unsafe()
        if self._addr_type == AddrType.BYTE:
            return (self.__cursor - self._base) // 8
        return self.__cursor - self._base

    def __enter__(self) -> DataSource:
        self.__with_safe = True
        return self

    def __exit__(self, e_type, value, traceback) -> bool:
        if e_type is None:
            # Data has been read successfully and we update the parent DataSource with
            # the current cursor location before this Cursor is discarded.
            if self.__parent is not None:
                if (
                    self.__parent._addr_type == AddrType.BYTE
                    and (self.__cursor - self._base) % 8
                ):
                    raise RuntimeError(
                        "Cannot return non-byte length to bytewise parent"
                    )
                self.__parent.__cursor = self.__cursor
                self.__parent.__has_child = False
                self.__parent.trim()
            return True
        if issubclass(e_type, fbe.FBError):
            if self._revertible:
                if self.__parent is not None:
                    self.__parent.__has_child = False
                return True
        raise

    def lower_bound(self) -> int:
        """Returns the bit address of the first byte in the buffers

        Returns:
            The bit address of the first byte in the buffers
        """
        return self.__bounds[0]

    def upper_bound(self) -> int:
        """Returns the bit address after the last byte in the buffers

        Returns:
            The bit address after the last byte in the buffers
        """
        return self.__bounds[-1]
