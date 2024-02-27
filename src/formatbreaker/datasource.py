"""Classes that provide a consistent buffered bitwise interface to byte data"""

from __future__ import annotations
from typing import Any, Optional, Type
from types import TracebackType
import io
import collections
import bisect
from enum import Enum
from formatbreaker.bitwisebytes import BitwiseBytes, bitlen
from formatbreaker.exceptions import FBError, FBNoDataError
from formatbreaker.util import uptobyte, downtobyte


class AddrType(Enum):
    """Used to indicate the addressing type of a DataManager instance or a Parser
    instance
    """

    BIT = 1
    BYTE = 2
    BYTE_STRICT = 3
    PARENT = 4


DATA_BUFFER_SIZE = 1024 * 8


class DataBuffer:
    """This class provides a buffered, bitwise addressable interface to a bytes or
    BufferIOBase object"""

    __slots__ = ("_bounds", "_buffers", "_stream_eof", "_stream")
    _bounds: collections.deque[int]
    _buffers: collections.deque[bytes]
    _stream_eof: bool
    _stream: io.BufferedIOBase

    def __init__(
        self,
        src: bytes | io.BufferedIOBase,
    ) -> None:
        """
        Args:
            src: The data source
        """
        self._bounds = collections.deque([0])
        self._buffers = collections.deque()
        if isinstance(src, bytes):
            self._stream_eof = True  # There is no stream, don't try to read from it
            self._buffers.append(src)  # No extra buffering, it's already in memory
            self._bounds.append(bitlen(src))
        elif isinstance(src, io.BufferedIOBase):  # type: ignore
            self._stream = src
            self._stream_eof = False
            self._load_from_stream(DATA_BUFFER_SIZE)
        else:
            raise NotImplementedError

    @property
    def lower_bound(self) -> int:
        """Returns the bit address of the first byte in the buffers

        Returns:
            The bit address of the first byte in the buffers
        """
        return self._bounds[0]

    @property
    def upper_bound(self) -> int:
        """Returns the bit address after the last byte in the buffers

        Returns:
            The bit address after the last byte in the buffers
        """
        return self._bounds[-1]

    def get_data(
        self, start: int, bit_length: int | None = None
    ) -> tuple[BitwiseBytes, int]:
        """Generates a single `BitwiseBytes` of the address range requested

        This method will attempt to read data from `self._stream` if there is not enough
        data in the buffer to satisfy the request.

        Args:
            start: Address of the first bit (inclusive)
            bit_length: The number of bits to return. Defaults to all remaining bits.
        Returns:
            A tuple with the bits requested and the address of the end bit (exclusive)
        """
        if start < self.lower_bound:
            raise IndexError("Addressed data no longer in DataBuffer")
        if bit_length is None:
            self._load_from_stream()
            stop = self.upper_bound
        else:
            if bit_length < 0:
                raise IndexError("Cannot read negative length.")
            stop = start + bit_length
            if stop > self.upper_bound:
                bits_needed = stop - self.upper_bound
                if self._load_from_stream(bits_needed) < bits_needed:
                    raise FBNoDataError

        return self._concatenate_bits_in_range(start, stop), stop

    def _concatenate_bits_in_range(self, start: int, stop: int):
        """Generates a single `BitwiseBytes` of the address range requested

        This method relies on the data already existing in `_buffers`

        Args:
            start: Address of the first bit (inclusive)
            stop: Address of the end bit (exclusive)

        Returns: The bits requested
        """
        assert stop > start >= 0

        length = stop - start

        start_buffer = bisect.bisect_right(self._bounds, start) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self._buffers)

        stop_buffer = bisect.bisect_left(self._bounds, stop) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self._buffers)

        start_buffer_start_bit = start - self._bounds[start_buffer]
        stop_buffer_stop_bit = stop - self._bounds[stop_buffer]

        start_buffer_start_byte = downtobyte(start_buffer_start_bit)
        stop_buffer_stop_byte = uptobyte(stop_buffer_stop_bit)

        if start_buffer == stop_buffer:
            byte_result = self._buffers[start_buffer][
                start_buffer_start_byte:stop_buffer_stop_byte
            ]

        elif start_buffer + 1 == stop_buffer:
            byte_result = (
                self._buffers[start_buffer][start_buffer_start_byte:]
                + self._buffers[stop_buffer][:stop_buffer_stop_byte]
            )
        else:
            byte_result = self._buffers[start_buffer][start_buffer_start_byte:]
            for i in range(start_buffer + 1, stop_buffer):
                byte_result = byte_result + self._buffers[i]
            byte_result = (
                byte_result + self._buffers[stop_buffer][:stop_buffer_stop_byte]
            )

        start_slice = start % 8
        stop_slice = start_slice + length
        return BitwiseBytes(byte_result, start_slice, stop_slice)

    def _load_from_stream(self, bit_length: int | None = None) -> int:
        """Reads bytes from the underlying stream into a buffer

        Args:
            bit_length: The minimum number of bits to read into the buffer. Reads all
            available data if undefined

        Raises:
            FBNoDataError: Raised if we have already hit EOF.

        Returns:
            Returns the number of bytes read.
        """
        if self._stream_eof:
            if bit_length is None:
                return 0  # Okay to read 0 bytes from an empty stream. Weird, but okay.
            raise FBNoDataError
        if bit_length is not None:
            byte_length = uptobyte(max(DATA_BUFFER_SIZE, bit_length))
            read_length = byte_length * 8
            data = self._stream.read(byte_length)
        else:
            read_length = float("inf")  # For _stream_eof logic
            data = self._stream.read()
            self._stream_eof = True
        data_length = bitlen(data)
        self._stream_eof = data_length < read_length
        if data_length == 0:
            return 0
        self._bounds.append(self.upper_bound + data_length)
        self._buffers.append(data)
        return data_length

    def trim(self, addr: int) -> None:
        """Discard any buffers that are unneeded

        This will always leave the most recent buffer untouched

        Args:
            addr: The first address we would like to keep in the buffers
        """
        assert addr <= self.upper_bound
        # This would imply that the cursor points to data we haven't read

        assert len(self._bounds) > 1
        # This would imply that we have have no buffers

        while len(self._bounds) > 2 and addr >= self._bounds[1]:
            del self._buffers[0]
            del self._bounds[0]


class DataManager:
    """This class holds a data buffer and manages addressing for Parsers.

    It holds the base address for relative addressing and tracks the current address as
    it reads data. When a nested Parser has a different addressing scheme (eg: bitwise
    vs bytewise, or relative to a new base), we create a child AddressManager that
    takes over address management. All AddressManagers must be created in a with
    statement. When a child AddressManager is active, the parent may not be used. For
    example:

    some_data = b'12345'
    with AddressManager(some_data) as parent:
        # Do stuff with parent
        with parent.make_child() as child:
            Do stuff with child
        # Do stuff with parent again

    When a with statement block exits normally, a child AddressManager updates the
    address of its parent to where the child finished reading. If an exception occurs,
    such as running out of data, this does not happen. However, if an AddressManager
    is declared revertible, FBError exceptions will be swallowed by that instance, and
    execution will continue after the associated with block, without any address update
    to the parent.
    """

    __slots__ = (
        "_buffer",
        "_with_safe",
        "_has_child",
        "_revertible",
        "_trim_safe",
        "_cursor",
        "_parent",
        "_base",
        "_addr_type",
    )

    _buffer: DataBuffer
    _with_safe: bool
    _has_child: bool
    _revertible: bool
    _trim_safe: bool
    _cursor: int
    _parent: DataManager | None
    _base: int
    _addr_type: AddrType

    def __init__(
        self,
        src: bytes | io.BufferedIOBase | DataManager,
        relative: bool = True,
        addr_type: AddrType = AddrType.PARENT,
        revertible: bool = False,
    ) -> None:
        """
        The constructor should not be used directly for creating a child instance. Use
        `make_child()`

        Args:
            src: A source of bytes data or a parent AddressManager
            relative: Whether the addressing is relative to cursor location on creation
            addr_type: Whether the addressing is bitwise or bytewise
            revertible: Whether the reads to this AddressManager and its children can
            fail and be reverted
        """
        self._with_safe = False
        self._revertible = revertible
        self._has_child = False
        self._addr_type = addr_type

        if isinstance(src, DataManager):

            self._parent = src
            self._parent._has_child = True
            self._trim_safe = src._trim_safe and not revertible
            self._buffer = src._buffer
            self._cursor = src._cursor
            if relative:
                self._base = self._cursor
            else:
                self._base = src._base
            if self._addr_type == AddrType.PARENT:
                self._addr_type = src._addr_type
        else:
            # No parent
            self._parent = None
            self._trim_safe = not revertible
            self._buffer = DataBuffer(src)
            self._cursor = 0
            self._base = 0
            if self._addr_type == AddrType.PARENT:
                self._addr_type = AddrType.BYTE

        if self._addr_type == AddrType.BYTE_STRICT:
            if self._cursor % 8:
                raise FBError("Strict byte addr_type must start on a byte boundary")

        if self._parent and self._parent._addr_type != self._addr_type and not relative:
            raise RuntimeError("Address type changes must use relative addr_type")

    @property
    def address(self) -> int:
        """Returns the current address

        Returns:
            The current read address, relative to `_base`, bitwise or bytewise
            according to `self.addr_type`
        """
        self._fail_if_unsafe()
        if self._addr_type == AddrType.BYTE:
            return (self._cursor - self._base) // 8
        return self._cursor - self._base

    def make_child(
        self,
        **kwargs: Any,
    ) -> DataManager:
        """Creates a child AddressManager with its own cursor and addressing

        Takes the same optional arguments as the constructor.

        Args:
            relative: Whether the addressing is relative to cursor location on creation
            addr_type: Whether the addressing is bitwise or bytewise
            revertible: Whether the reads to this AddressManager and its children can
            fail and be reverted
        Returns:
            The child AddressManager
        """
        self._fail_if_unsafe()

        return self.__class__(self, **kwargs)

    def read(self, length: int | None = None) -> bytes:
        """Reads from the bufferer

        Args:
            length: The number of bits or bytes to read based on `AddrType.BYTE`. Reads
            all data available if undefined.

        Returns:
            The requested data, if available. Bits are converted to right justified
            bytes.
        """
        self._fail_if_unsafe()

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
        self._fail_if_unsafe()
        if byte_length is None:
            return bytes(self.read_bits())
        if byte_length == 0:
            return b""
        return bytes(self.read_bits(bit_length=byte_length * 8))

    def read_bits(self, bit_length: int | None = None) -> BitwiseBytes:
        """Reads bits from the buffer

        Args:
            length: The number of bits to read. Reads all data available if undefined.

        Returns:
            The requested bits, if available
        """
        self._fail_if_unsafe()
        start_addr = self._cursor

        if bit_length == 0:
            return BitwiseBytes(b"")

        (result, stop_addr) = self._buffer.get_data(start_addr, bit_length)
        self._cursor = stop_addr
        self._trim()
        return result

    def _trim(self) -> None:
        """Discard any buffers that have been read and are unneeded"""
        self._fail_if_unsafe()
        if self._trim_safe:
            self._buffer.trim(self._cursor)

    def __enter__(self) -> DataManager:
        self._with_safe = True
        return self

    def __exit__(
        self,
        e_type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool | None:
        self._with_safe = False  # Protects against the instance being reused
        if e_type is None:
            # Data has been read successfully and we update the parent AddressManager
            # with the current cursor location before this Cursor is discarded.
            if self._parent is not None:
                if (
                    self._parent._addr_type == AddrType.BYTE
                    and (self._cursor - self._base) % 8
                ):
                    raise RuntimeError(
                        "Cannot return non-byte length to bytewise parent"
                    )
                self._parent._cursor = self._cursor
                self._parent._has_child = False
                self._parent._trim()
            return True
        if issubclass(e_type, FBError):
            if self._revertible:
                if self._parent is not None:
                    self._parent._has_child = False
                return True
        raise

    def _fail_if_unsafe(self) -> None:
        """Raises an error if it's not safe to use this instance

        Called by other methods to prevent use of an instance with a child in use,
        or an instance generated outside a with statement

        Raises:
            RuntimeError: Raised if it's unsafe to use this instance
        """
        if self._has_child:
            raise RuntimeError("Attemped to access a AddressManager with a child.")
        if not self._with_safe:
            raise RuntimeError("AddressManager used outside a with statement.")
