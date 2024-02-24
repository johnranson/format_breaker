"""Decoding and Translating Parsers

The classes in this module add functionality to existing parsers by adding
`_decode()` logic. They only implement _decode (and _init, if needed.)
"""

from __future__ import annotations
from typing import override, Any
import struct
import uuid
from formatbreaker.basictypes import Byte, Bytes, BitWord, Bit
from formatbreaker.core import Translator, Parser, StaticTranslator
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


class BitFlags(BitWord):
    """Reads a number of bits from the data"""

    _default_backup_label = "Flags"

    @override
    def decode(self, data: BitwiseBytes) -> list[bool]:  # type: ignore[override]
        return data.to_bools()


class BitUInt(BitWord):
    _default_backup_label = "UInt"

    @override
    def decode(self, data: BitwiseBytes) -> int:
        """Decodes the bits into an unsigned integer

        Args:
            data: A string of bits

        Returns:
            The bits converted to an unsigned integer
        """
        return int(data)


def Int(size, byteorder, signed):
    return StaticTranslator(
        Bytes(size),
        lambda data: int.from_bytes(data, byteorder, signed=signed),
        ("Int" if signed else "UInt") + str(8 * size),
    )


Int32L = Int(4, "little", signed=True)
Int16L = Int(2, "little", signed=True)
Int8 = Int(1, "little", signed=True)

UInt32L = Int(4, "little", signed=False)
UInt16L = Int(2, "little", signed=False)
UInt8 = Int(1, "little", signed=False)

Int32B = Int(4, "big", signed=True)
Int16B = Int(2, "big", signed=True)

UInt32B = Int(4, "big", signed=False)
UInt16B = Int(2, "big", signed=False)


def DeStructor(fmt, backup_label=None):
    return StaticTranslator(
        Bytes(struct.calcsize(fmt)),
        lambda data: struct.unpack(fmt, data)[0],
        backup_label,
    )


Float32L = DeStructor("<f", "Float32")
Float64L = DeStructor("<d", "Float64")


UuidL = StaticTranslator(Bytes(16), lambda data: uuid.UUID(bytes_le=data), "UUID")
UuidB = StaticTranslator(Bytes(16), lambda data: uuid.UUID(bytes=data), "UUID")


class Const(Translator):
    def __init__(self, value: Any, parser: Parser | None = None) -> None:
        if parser is None:
            if isinstance(value, bool):
                parser = Bit
            elif isinstance(value, int):
                if value < 0 or value > 255:
                    raise ValueError
                parser = UInt8
            elif isinstance(value, bytes):
                parser = Bytes(len(value))
            elif isinstance(value, BitwiseBytes):
                parser = BitWord(len(value))
            else:
                raise TypeError
        self._value = value
        super().__init__(parser, "Const")

    @override
    def _translate(self, data: Any) -> Any:
        decoded_data = self._parsable.decode(data)
        if self._value != decoded_data:
            raise FBError("Constant not matched")
        return decoded_data


def BitWordConst(value: BitwiseBytes | bytes | int, bit_length: int | None = None):
    if isinstance(value, BitwiseBytes):
        if bit_length is not None:
            v = value[0:bit_length]
        else:
            v = value
    elif isinstance(value, bytes):  # type: ignore
        v = BitwiseBytes(value, 0, bit_length)
    elif isinstance(value, int):  # type: ignore
        v = BitwiseBytes(value.to_bytes(), 0, bit_length)
    else:
        raise TypeError
    return Const(v)


BitOne = Const(True)
BitZero = Const(False)
