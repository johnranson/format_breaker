"""Decoding Parsers

The classes in this module add functionality to existing parsers by adding
`_decode()` logic. They only implement _decode (and _init, if needed.)
"""

from __future__ import annotations
from typing import override, Any
import struct
import uuid
from formatbreaker.basictypes import ByteParser, Byte, Bytes, BitWord, Bit
from formatbreaker.core import Translator, Parser
from formatbreaker.exceptions import FBError
from formatbreaker.bitwisebytes import BitwiseBytes


class ByteFlag(ByteParser):
    """Reads 1 byte as a boolean"""

    _true_value: int | None
    _default_backup_label = "Flag"

    @override
    def __init__(
        self,
        true_value: bytes | int | None = None,
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


class ConstClass(Translator):
    def __init__(self, parser: Parser, value: Any) -> None:
        super().__init__(parser, "Const")
        self._value = value

    @override
    def _translate(self, data: Any) -> Any:
        if self._value != data:
            raise FBError("Constant not matched")
        return data


def make_const(parser: Parser):
    def const_func(value: Any):
        return ConstClass(parser, value)

    return const_func


BitOne = ConstClass(Bit, True)
BitZero = ConstClass(Bit, False)

ByteConst = make_const(Byte)


def BytesConst(data: bytes):
    ConstClass(Bytes(len(data)), data)


def BitWordConst(value: BitwiseBytes | bytes | int, bit_length: int | None = None):
    if isinstance(value, BitwiseBytes):
        v = int(value)
        if bit_length is None:
            bit_length = len(value)
    elif isinstance(value, bytes):  # type: ignore
        v = int(BitwiseBytes(value, 0, bit_length))
        if bit_length is None:
            raise ValueError
    elif isinstance(value, int):  # type: ignore
        v = value
        if bit_length is None:
            raise ValueError
    else:
        raise TypeError
    return ConstClass(BitWord(bit_length), v)


class BitFlags(BitWord):
    """Reads a number of bits from the data"""

    _default_backup_label = "Const"

    @override
    def _decode(self, data: BitwiseBytes) -> list[bool]:  # type: ignore[override]
        # The _decode
        return data.to_bools()


class IntL(Translator):
    @override
    def _translate(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=True)


class UIntL(Translator):
    @override
    def _translate(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=False)


Int32L = IntL(Bytes(4), "Int32")
Int16L = IntL(Bytes(2), "Int16")
Int8 = IntL(Bytes(1), "Int8")

UInt32L = UIntL(Bytes(4), "UInt32")
UInt16L = UIntL(Bytes(2), "UInt16")
UInt8 = UIntL(Bytes(1), "UInt8")


class Float32LParser(Bytes):
    """Reads 4 bytes as a little endian single precision float"""

    _default_backup_label = "Float32"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(4)

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
        print(self._backup_label)
        return struct.unpack("<f", data)[0]


Float32L = Float32LParser()


class Float64LParser(Bytes):
    """Reads 8 bytes as a little endian double precision float"""

    _default_backup_label = "Float64"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(8)

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

    _default_backup_label = "UUID"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(16)

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

    _default_backup_label = "UUID"

    @override
    def __init__(self, label: str | None = None, *, addr: int | None = None) -> None:
        super().__init__(16)

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
