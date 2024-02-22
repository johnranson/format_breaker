"""Decoding Parsers

The classes in this module add functionality to existing parsers by adding
`_decode()` logic. They only implement _decode (and _init, if needed.)
"""

from __future__ import annotations
from typing import override
import struct
import uuid
from formatbreaker.basictypes import ByteParser, Bytes, BitWord, BitParser
from formatbreaker.exceptions import FBError
from formatbreaker.bitwisebytes import BitwiseBytes


class ByteFlag(ByteParser):
    """Reads 1 byte as a boolean"""

    _true_value: int | None
    _backup_label = "Flag"

    @override
    def __init__(
        self,
        true_value: bytes | int | None = None,
        label: str | None = None,
        *,
        addr: int | None = None,
    ) -> None:
        """
        Args:
            true_value: The only value which the parser will interpret as True, if
                defined.
        """
        if isinstance(true_value, bytes):
            if len(true_value) != 1:
                raise ValueError
            self._true_value = true_value[0]
        elif isinstance(true_value, int):
            self._true_value = true_value
            if self._true_value < 0 or self._true_value > 255:
                raise ValueError
        elif true_value is None:
            self._true_value = None
        else:
            raise TypeError
        if true_value == 0:
            raise ValueError

        super().__init__()

    @override
    def _decode(self, data: bytes) -> bool:
        if not data[0]:
            return False
        if self._true_value:
            if data[0] != self._true_value:
                raise FBError("Value to decode is not '0' or self._true_value")
        return True


class BitOneParser(BitParser):
    """Fails parsing if a bit isn't 1"""

    _backup_label = "Const"

    @override
    def _decode(self, data: bool) -> bool:
        if not super()._decode(data):
            raise FBError("Constant not matched")
        return True


BitOne = BitOneParser()


class BitZeroParser(BitParser):
    """Fails parsing if a bit isn't 0"""

    _backup_label = "Const"

    @override
    def _decode(self, data: bool) -> bool:
        if super()._decode(data):
            raise FBError("Constant not matched")
        return False


BitZero = BitZeroParser()


class BitWordConst(BitWord):
    """Fails parsing if a word doesn't match a constant value"""

    _backup_label = "Const"

    @override
    def __init__(
        self,
        value: BitwiseBytes | tuple[bytes, int],
        label: str | None = None,
        *,
        addr: int | None = None,
    ) -> None:
        if isinstance(value, BitwiseBytes):
            self._value = BitwiseBytes(value)
            bit_length = len(self._value)
        elif isinstance(value, tuple):  # type: ignore
            (dat, bit_length) = value
            self._value = BitwiseBytes(dat, 0, bit_length)
        else:
            raise TypeError

        super().__init__(bit_length, label, addr=addr)

    @override
    def _decode(self, data: BitwiseBytes) -> int:
        if self._value != data:
            print(int(self._value))
            print(int(data))
            raise FBError("Constant not matched")
        return int(self._value)


class BitFlags(BitWord):
    """Reads a number of bits from the data"""

    _backup_label = "Const"

    @override
    def _decode(self, data: BitwiseBytes) -> list[bool]:  # type: ignore[override]
        # The _decode
        return data.to_bools()


class Int32LParser(Bytes):
    """Reads 4 bytes as a signed, little endian integer"""

    _backup_label = "Int32"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(4, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a signed integer from 4 little endian bytes.

        Args:
            data: Four little endian bytes encoding an signed integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=True)


Int32L = Int32LParser()


class UInt32LParser(Bytes):
    """Reads 4 bytes as a unsigned, little endian integer"""

    _backup_label = "UInt32"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(4, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a unsigned integer from 4 little endian bytes.

        Args:
            data: Four little endian bytes encoding an unsigned integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=False)


UInt32L = UInt32LParser()


class Int16LParser(Bytes):
    """Reads 2 bytes as a signed, little endian integer"""

    _backup_label = "Int16"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(2, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a signed integer from 2 little endian bytes.

        Args:
            data: Two little endian bytes encoding an signed integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=True)


Int16L = Int16LParser()


class UInt16LParser(Bytes):
    """Reads 2 bytes as a unsigned, little endian integer"""

    _backup_label = "UInt16"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(2, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a unsigned integer from 2 little endian bytes.

        Args:
            data: Two little endian bytes encoding an unsigned integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=False)


UInt16L = UInt16LParser()


class Int8Parser(ByteParser):
    """Reads 1 byte as a signed integer"""

    _backup_label = "Int8"

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a signed integer from one byte.

        Args:
            data: One byte

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=True)


Int8 = Int8Parser()


class UInt8Parser(ByteParser):
    """Reads 1 byte as an unsigned integer"""

    _backup_label = "UInt8"

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes an unsigned integer from one byte.

        Args:
            data: One byte

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=False)


UInt8 = UInt8Parser()


class Float32LParser(Bytes):
    """Reads 4 bytes as a little endian single precision float"""

    _backup_label = "Float32"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(4, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> float:
        """Decodes a single precision floating point number from little endian
        bytes.

        Args:
            data: 4 little endian bytes encoding a single precision floating point
                number

        Returns:
            The decoded number
        """
        return struct.unpack("<f", data)[0]


Float32L = Float32LParser()


class Float64LParser(Bytes):
    """Reads 8 bytes as a little endian double precision float"""

    _backup_label = "Float64"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(8, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> float:
        """Decodes a double precision floating point number from little endian
        bytes.

        Args:
            data: 8 little endian bytes encoding a double precision floating point
                number

        Returns:
            The decoded number
        """

        return struct.unpack("<d", data)[0]


Float64L = Float64LParser()


class UuidLParser(Bytes):
    """Reads 16 bytes as a UUID (Little Endian words)"""

    _backup_label = "UUID"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(16, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> uuid.UUID:
        """Decodes a UUID with little endian words.

        Args:
            data: A 16 byte binary UUID with little endian words

        Returns:
            The decoded UUID
        """
        return uuid.UUID(bytes_le=data)


UuidL = UuidLParser()


class UuidBParser(Bytes):
    """Reads 16 bytes as a UUID (Big Endian words)"""

    _backup_label = "UUID"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(16, label, addr=addr)

    @override
    def _decode(self, data: bytes) -> uuid.UUID:
        """Decodes a UUID with big endian words.

        Args:
            data: A 16 byte binary UUID with big endian words

        Returns:
            The decoded UUID
        """
        return uuid.UUID(bytes=data)


UuidB = UuidBParser()
