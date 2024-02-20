"""Code that is mostly used internally"""

from __future__ import annotations
import io
import collections
import bisect
import enum
import formatbreaker.bitwisebytes as bitwisebytes
import formatbreaker.exceptions as fbe
import formatbreaker.util as fbu


AddrType = enum.Enum("AddrType", ["BIT", "BYTE", "BYTE_STRICT", "PARENT"])
DATA_BUFFER_SIZE = 1024 * 8


class DataBufferer:
    __slots__ = ("__bounds", "__buffers", "__stream_eof", "__stream")
    __bounds: collections.deque[int]
    __buffers: collections.deque[bytes]
    __stream_eof: bool
    __stream: io.BufferedIOBase

    def __init__(
        self,
        src: bytes | io.BufferedIOBase | DataSource,
    ) -> None:

        self.__bounds = collections.deque([0])
        self.__buffers = collections.deque()
        if isinstance(src, bytes):
            self.__buffers.append(src)
            self.__bounds.append(bitwisebytes.bitlen(src))
            self.__stream_eof = True
        elif isinstance(src, io.BufferedIOBase):
            self.__stream = src
            self.__stream_eof = False
            self._read_into_buffer(DATA_BUFFER_SIZE)
        else:
            raise NotImplementedError

    def _load_data_into_buffers(self, start: int, bit_length: int | None) -> int:
        if start < self.lower_bound:
            raise IndexError("Cursor points to data no longer in buffers")
        if start > self.upper_bound:
            raise IndexError("Cursor points past end of buffered data.")

        if bit_length is not None:
            if bit_length < 0:
                raise IndexError("Cannot read negative length.")

            stop = start + bit_length
            if stop > self.upper_bound:
                bits_needed = stop - self.upper_bound
                if self._read_into_buffer(bits_needed) < bits_needed:
                    raise fbe.FBNoDataError
        else:
            self._read_into_buffer()
            stop = self.upper_bound
        return self._get_data_from_buffers(start, stop), stop

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
        if self.__stream_eof:
            if bit_length is None:
                return 0
            raise fbe.FBNoDataError
        if bit_length is not None:
            byte_length = fbu.uptobyte(max(DATA_BUFFER_SIZE, bit_length))
            read_length = byte_length * 8
            data = self.__stream.read(byte_length)
        else:
            read_length = float("inf")
            data = self.__stream.read()
            self.__stream_eof = True
        data_length = bitwisebytes.bitlen(data)
        self.__stream_eof = data_length < read_length
        self.__bounds.append(self.__bounds[-1] + data_length)
        self.__buffers.append(data)
        return data_length

    @property
    def lower_bound(self) -> int:
        """Returns the bit address of the first byte in the buffers

        Returns:
            The bit address of the first byte in the buffers
        """
        return self.__bounds[0]

    @property
    def upper_bound(self) -> int:
        """Returns the bit address after the last byte in the buffers

        Returns:
            The bit address after the last byte in the buffers
        """
        return self.__bounds[-1]

    def trim(self, addr) -> None:
        """Discard any buffers that have been read and are unneeded"""
        assert addr <= self.upper_bound
        # This would imply that the cursor points to data we haven't read

        assert len(self.__bounds) > 1
        # This would imply that we have have no buffers

        while addr > self.__bounds[1]:
            del self.__buffers[0]
            del self.__bounds[0]


class DataSource:
    """This class holds a source of data, buffers it, and keeps a nested contexts
    storing address data allowing reversion of failed reads."""

    __slots__ = (
        "_bufferer",
        "__with_safe",
        "__has_child",
        "__revertible",
        "__trim_safe",
        "__cursor",
        "__parent",
        "__base",
        "__addr_type",
    )

    _bufferer: DataBufferer
    __with_safe: bool
    __has_child: bool
    __revertible: bool
    __trim_safe: bool
    __cursor: int
    __parent: DataSource | None
    __base: int
    __addr_type: AddrType

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
            self.__trim_safe = src.__trim_safe and not revertible
            self._bufferer = src._bufferer
            self.__cursor = src.__cursor
            self.__parent = src
            self.__parent.__has_child = True
            if relative:
                self.__base = self.__cursor
            else:
                self.__base = src.__base

        else:
            # No parent
            self.__trim_safe = not revertible
            self.__parent = None  # Must be first
            if addr_type == AddrType.PARENT:
                self.__addr_type = AddrType.BYTE
            else:
                self.__addr_type == addr_type

            self._bufferer = DataBufferer(src)

            self.__cursor = 0
            self.__base = 0

        match addr_type:
            case AddrType.PARENT:
                if self.__parent is not None:
                    self.__addr_type = src.__addr_type
                else:
                    self.__addr_type = AddrType.BYTE
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

        if self.__parent and self.__parent.__addr_type != addr_type and not relative:
            raise RuntimeError("Address type changes must use relative addr_type")


    def fail_if_unsafe(self) -> None:
        if self.__has_child:
            raise RuntimeError("Attemped to access a DataSource with a child.")
        if not self.__with_safe:
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

        if self.__addr_type == AddrType.BYTE:
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

        if bit_length is not None:
            if bit_length == 0:
                return bitwisebytes.BitwiseBytes(b"")

        (result, stop_addr) = self._bufferer._load_data_into_buffers(start_addr, bit_length)
        self.__cursor = stop_addr
        self.trim()
        return result

    def trim(self) -> None:
        """Discard any buffers that have been read and are unneeded"""
        self.fail_if_unsafe()
        if not self.__trim_safe:
            return

        self._bufferer.trim(self.__cursor)

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

    @property
    def address(self) -> int:
        """Returns the current address

        Returns:
            The current read address, bitwise or bytewise according to `self.addr_type`
        """
        self.fail_if_unsafe()
        if self.__addr_type == AddrType.BYTE:
            return (self.__cursor - self.__base) // 8
        return self.__cursor - self.__base

    def __enter__(self) -> DataSource:
        self.__with_safe = True
        return self

    def __exit__(self, e_type, value, traceback) -> bool:
        self.__with_safe = False  # Protects against the instance being reused
        if e_type is None:
            # Data has been read successfully and we update the parent DataSource with
            # the current cursor location before this Cursor is discarded.
            if self.__parent is not None:
                if (
                    self.__parent.__addr_type == AddrType.BYTE
                    and (self.__cursor - self.__base) % 8
                ):
                    raise RuntimeError(
                        "Cannot return non-byte length to bytewise parent"
                    )
                self.__parent.__cursor = self.__cursor
                self.__parent.__has_child = False
                self.__parent.trim()
            return True
        if issubclass(e_type, fbe.FBError):
            if self.__revertible:
                if self.__parent is not None:
                    self.__parent.__has_child = False
                return True
        raise
