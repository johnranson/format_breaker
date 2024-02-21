"""Code that is mostly used internally"""

from __future__ import annotations
import io
import collections
import bisect
import enum
from formatbreaker.bitwisebytes import BitwiseBytes, bitlen
import formatbreaker.exceptions as fbe
import formatbreaker.util as fbu


AddrType = enum.Enum("AddrType", ["BIT", "BYTE", "BYTE_STRICT", "PARENT"])
DATA_BUFFER_SIZE = 1024 * 8


class DataBuffer:
    """This class provides a buffered, bitwise addressable interface to bytes or a
    BufferIOBase"""

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
            src: The source of the data to be buffered
        """
        self._bounds = collections.deque([0])
        self._buffers = collections.deque()
        if isinstance(src, bytes):
            self._stream_eof = True  # This prevents reading from a non-existent string
            self._buffers.append(src)
            self._bounds.append(bitlen(src))
        elif isinstance(src, io.BufferedIOBase):
            self._stream = src
            self._stream_eof = False
            self._read_from_stream(DATA_BUFFER_SIZE)
        else:
            raise NotImplementedError

    def get_data(self, start: int, bit_length: int | None) -> tuple[BitwiseBytes, int]:
        """Generates a single `BitwiseBytes` of the address range requested

        This method will attempt to read data if it is not yet stored in `_buffers`

        Args:
            start: Address of the first bit to be included
            bit_length: The number of bits to return
        Returns:
            A tuple with the bits requested and the address of the next bit after the
            data
        """
        if start < self.lower_bound:
            raise IndexError("Addressed data no longer in DataBuffer")
        if bit_length is not None:
            if bit_length < 0:
                raise IndexError("Cannot read negative length.")
            stop = start + bit_length
            if stop > self.upper_bound:
                bits_needed = stop - self.upper_bound
                if self._read_from_stream(bits_needed) < bits_needed:
                    raise fbe.FBNoDataError
        else:
            self._read_from_stream()
            stop = self.upper_bound
        return self._concatenate_bits(start, stop), stop

    def _concatenate_bits(self, start: int, stop: int):
        """Generates a single `BitwiseBytes` of the address range requested

        This method relies on the data already existing in `_buffers`

        Args:
            start: Address of the first bit to be included
            stop: Address of the first bit not included after the range

        Returns: The bits requested
        """
        assert stop > start >= 0

        start_buffer = bisect.bisect_right(self._bounds, start) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self._buffers)

        stop_buffer = bisect.bisect_left(self._bounds, stop) - 1
        assert start_buffer >= 0
        assert start_buffer < len(self._buffers)

        start_buffer_start = start - self._bounds[start_buffer]
        stop_buffer_stop = stop - self._bounds[stop_buffer]

        start_buffer_start = fbu.downtobyte(start_buffer_start)
        stop_buffer_stop = fbu.uptobyte(stop_buffer_stop)

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

    def _read_from_stream(self, bit_length=None) -> int:
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
                return 0
            raise fbe.FBNoDataError
        if bit_length is not None:
            byte_length = fbu.uptobyte(max(DATA_BUFFER_SIZE, bit_length))
            read_length = byte_length * 8
            data = self._stream.read(byte_length)
        else:
            read_length = float("inf")
            data = self._stream.read()
            self._stream_eof = True
        data_length = bitlen(data)
        self._stream_eof = data_length < read_length
        self._bounds.append(self.upper_bound + data_length)
        self._buffers.append(data)
        return data_length

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

    def trim(self, addr) -> None:
        """Discard any buffers that have been read and are unneeded"""
        assert addr <= self.upper_bound
        # This would imply that the cursor points to data we haven't read

        assert len(self._bounds) > 1
        # This would imply that we have have no buffers

        while addr > self._bounds[1]:
            del self._buffers[0]
            del self._bounds[0]


class DataSource:
    """This class holds a source of data, buffers it, and keeps a nested contexts
    storing address data allowing reversion of failed reads."""

    __slots__ = (
        "_bufferer",
        "_with_safe",
        "_has_child",
        "_revertible",
        "_trim_safe",
        "_cursor",
        "_parent",
        "_base",
        "_addr_type",
    )

    _bufferer: DataBuffer
    _with_safe: bool
    _has_child: bool
    _revertible: bool
    _trim_safe: bool
    _cursor: int
    _parent: DataSource | None
    _base: int
    _addr_type: AddrType

    def __init__(
        self,
        src: bytes | io.BufferedIOBase | DataSource,
        relative: bool = True,
        addr_type: AddrType = AddrType.PARENT,
        revertible: bool = False,
    ) -> None:
        self._with_safe = False
        self._revertible = revertible
        self._has_child = False
        self._addr_type = addr_type
        if isinstance(src, DataSource):

            self._parent = src
            self._parent._has_child = True
            self._trim_safe = src._trim_safe and not revertible
            self._bufferer = src._bufferer
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
            self._bufferer = DataBuffer(src)
            self._cursor = 0
            self._base = 0
            if self._addr_type == AddrType.PARENT:
                self._addr_type = AddrType.BYTE

        if self._addr_type == AddrType.BYTE_STRICT:
            if self._cursor % 8:
                raise fbe.FBError("Strict byte addr_type must start on a byte boundary")

        if self._parent and self._parent._addr_type != addr_type and not relative:
            raise RuntimeError("Address type changes must use relative addr_type")

    def fail_if_unsafe(self) -> None:
        """Raises an error if it's not safe to use this instance

        Called by other methods to prevent use if this instance has a child in use,
        or if this instance was generated outside a with statement

        Raises:
            RuntimeError: Raised if it's unsafe to use this instance
        """
        if self._has_child:
            raise RuntimeError("Attemped to access a DataSource with a child.")
        if not self._with_safe:
            raise RuntimeError("Datasource used outside a with statement.")

    def read(self, length: int | None = None) -> bytes:
        """Reads from the bufferer

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

    def read_bits(self, bit_length: int | None = None) -> BitwiseBytes:
        """Reads bits from the buffer

        Args:
            length: The number of bits to read. Reads all data available if undefined.

        Returns:
            The requested bits, if available
        """
        self.fail_if_unsafe()
        start_addr = self._cursor

        if bit_length is not None:
            if bit_length == 0:
                return BitwiseBytes(b"")

        (result, stop_addr) = self._bufferer.get_data(start_addr, bit_length)
        self._cursor = stop_addr
        self.trim()
        return result

    def trim(self) -> None:
        """Discard any buffers that have been read and are unneeded"""
        self.fail_if_unsafe()
        if not self._trim_safe:
            return

        self._bufferer.trim(self._cursor)

    def make_child(
        self,
        relative: bool | None = None,
        addr_type: AddrType | None = None,
        revertible: bool | None = None,
    ) -> DataSource:
        """Creates a child DataSource with its own cursor and addressing

        Arguments will not be passed if they are None, allowing the constructor defaults

        Args:
            relative: Whether the addressing is relative to cursor location on creation
            addr_type: Whether the addressing is bitwise or bytewise
            revertible: Whether the reads to this DataSource and its children can fail
            and be reverted
        Returns:
            The child DataSource
        """
        self.fail_if_unsafe()

        params = {
            "relative": relative,
            "addr_type": addr_type,
            "revertible": revertible,
        }
        passed_params = {k: v for k, v in params.items() if v is not None}
        # Only pass params actually provided.

        return self.__class__(self, **passed_params)

    @property
    def address(self) -> int:
        """Returns the current address

        Returns:
            The current read address, relative to `_base`, bitwise or bytewise
            according to `self.addr_type`
        """
        self.fail_if_unsafe()
        if self._addr_type == AddrType.BYTE:
            return (self._cursor - self._base) // 8
        return self._cursor - self._base

    def __enter__(self) -> DataSource:
        self._with_safe = True
        return self

    def __exit__(self, e_type, value, traceback) -> bool:
        self._with_safe = False  # Protects against the instance being reused
        if e_type is None:
            # Data has been read successfully and we update the parent DataSource with
            # the current cursor location before this Cursor is discarded.
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
                self._parent.trim()
            return True
        if issubclass(e_type, fbe.FBError):
            if self._revertible:
                if self._parent is not None:
                    self._parent._has_child = False
                return True
        raise
