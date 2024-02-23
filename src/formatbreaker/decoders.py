"""Decoding and Translating Parsers

The classes in this module add functionality to existing parsers by adding
`_decode()` logic. They only implement _decode (and _init, if needed.)
"""

from __future__ import annotations
from typing import override, Any
import struct
import uuid
from formatbreaker.basictypes import Byte, Bytes, BitWord, Bit
from formatbreaker.core import Translator, Parser, make_translator
from formatbreaker.exceptions import FBError
from formatbreaker.bitwisebytes import BitwiseBytes


class ByteFlag(Translator):
    """Reads as a boolean"""

    _true_value: int | None

    def __init__(self, true_value: Any = None, false_value: Any = b"\0") -> None:
        if true_value == false_value:
            raise ValueError
        super().__init__(Byte, "Flag")
        self._true_value = true_value
        self._false_value = false_value

    @override
    def _translate(self, data: Any) -> bool:
        if data == self._false_value:
            return False
        if self._true_value is None:
            return True
        if data == self._true_value:
            return True
        raise FBError()


class Const(Translator):
    def __init__(self, parser: Parser, value: Any) -> None:
        super().__init__(parser, "Const")
        self._value = value

    @override
    def _translate(self, data: Any) -> Any:
        decoded_data = self._parsable._decode(data)
        if self._value != decoded_data:
            raise FBError("Constant not matched")
        return decoded_data


def make_const(parser: Parser):
    def const_func(value: Any):
        return Const(parser, value)

    return const_func


BitOne = Const(Bit, True)
BitZero = Const(Bit, False)

ByteConst = make_const(Byte)

def BytesConst(data: bytes):
    Const(Bytes(len(data)), data)


def BitWordConst(value: BitwiseBytes | bytes | int, bit_length: int | None = None):
    if isinstance(value, BitwiseBytes):
        v = int(value)
        if bit_length is None:
            bit_length = len(value)
    elif isinstance(value, bytes):  # type: ignore
        v = int(BitwiseBytes(value, 0, bit_length))
    elif isinstance(value, int):  # type: ignore
        v = value
    else:
        raise TypeError
    if bit_length is None:
        raise ValueError
    return Const(BitWord(bit_length), v)


class BitFlags(BitWord):
    """Reads a number of bits from the data"""

    _default_backup_label = "Const"

    @override
    def _decode(self, data: BitwiseBytes) -> list[bool]:  # type: ignore[override]
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


class DeStructor(Translator):
    def __init__(self, fmt, backup_label=None) -> None:
        parser = Bytes(struct.calcsize(fmt))
        super().__init__(parser, backup_label)
        self._fmt = fmt

    @override
    def _translate(self, data: Any) -> Any:
        return struct.unpack(self._fmt, data)[0]


Float32L = DeStructor("<f", "Float32")
Float64L = DeStructor("<d", "Float64")


UuidL = make_translator(Bytes(16), lambda data: uuid.UUID(bytes_le=data), "UUID")
UuidB = make_translator(Bytes(16), lambda data: uuid.UUID(bytes=data), "UUID")
