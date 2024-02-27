"""Parsers that don't directly read data

The classes in this module add functionality to existing parsers, and don't directly
read data from the DataManager
"""

from __future__ import annotations
from typing import override, Any, Literal, ClassVar
import struct
import uuid
from formatbreaker.basictypes import Byte, Bytes, BitWord, Bit
from formatbreaker.core import Modifier, Parser, Translator
from formatbreaker.exceptions import FBError
from formatbreaker.bitwisebytes import BitwiseBytes


class Flag(Modifier):
    """Reads as a boolean"""

    _true_value: Any | None
    _false_value: Any | None

    def __init__(
        self, parser: Parser, false_value: Any, true_value: Any = None
    ) -> None:
        if true_value == false_value:
            raise ValueError
        super().__init__(parser, "Flag")
        self._true_value = true_value
        self._false_value = false_value

    @override
    def translate(self, data: Any) -> bool:
        if data == self._false_value:
            return False
        if self._true_value is None:
            return True
        if data == self._true_value:
            return True
        raise FBError()


def ByteFlag(true_value: Any = None) -> Parser:  # pylint: disable=invalid-name
    """Creates a parser that interprets a byte as a boolean

    Args:
        true_value: The only value interpreted as true, if set

    Returns:
        A parser instance
    """
    return Flag(Byte, b"\0", true_value)


class BitFlags(BitWord):
    """Reads a number of bits from the data as booleans"""

    _default_backup_label: ClassVar[str] = "Flags"

    @override
    def translate(self, data: BitwiseBytes) -> list[bool]:  # type: ignore[override]
        return data.to_bools()


class BitUInt(BitWord):
    """Reads a number of bits from the data as an unsigned integer"""

    _default_backup_label: ClassVar[str] = "UInt"

    @override
    def translate(self, data: BitwiseBytes) -> int:
        """Decodes the bits into an unsigned integer

        Args:
            data: A string of bits

        Returns:
            The bits converted to an unsigned integer
        """
        return int(data)


def IntParser(
    size: int, byteorder: Literal["little", "big"], signed: bool
):  # pylint: disable=invalid-name
    """Creates a parser instance that interprets bytes as an integer format

    Args:
        size: The number of bytes in the integer format
        byteorder: The endianness of the integer format
        signed: Whether the interger is signed

    Returns:
        A parser instances
    """
    return Translator(
        Bytes(size),
        lambda data: int.from_bytes(data, byteorder, signed=signed),
        ("Int" if signed else "UInt") + str(8 * size),
    )


Int32L = IntParser(4, "little", signed=True)
Int16L = IntParser(2, "little", signed=True)
Int8 = IntParser(1, "little", signed=True)

UInt32L = IntParser(4, "little", signed=False)
UInt16L = IntParser(2, "little", signed=False)
UInt8 = IntParser(1, "little", signed=False)

Int32B = IntParser(4, "big", signed=True)
Int16B = IntParser(2, "big", signed=True)

UInt32B = IntParser(4, "big", signed=False)
UInt16B = IntParser(2, "big", signed=False)


def DeStructor(
    fmt: str, backup_label: str | None = None
):  # pylint: disable=invalid-name
    """Creates a parser instance that interprets a number of bytes using a struct format string

    Args:
        backup_label: What the parser output is labeled in absence of a label

    Returns:
        A parser instances
    """
    return Translator(
        Bytes(struct.calcsize(fmt)),
        lambda data: struct.unpack(fmt, data)[0],
        backup_label,
    )


Float32L = DeStructor("<f", "Float32")
Float64L = DeStructor("<d", "Float64")


UuidL = Translator(Bytes(16), lambda data: uuid.UUID(bytes_le=data), "UUID")
UuidB = Translator(Bytes(16), lambda data: uuid.UUID(bytes=data), "UUID")


class Const(Modifier):
    """Fails parsing if the contained parser's output is not a fixed value"""

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
    def translate(self, data: Any) -> Any:
        decoded_data = self._parser.translate(data)
        if self._value != decoded_data:
            raise FBError("Constant not matched")
        return decoded_data


def BitWordConst(
    value: BitwiseBytes | bytes | int, bit_length: int | None = None
):  # pylint: disable=invalid-name
    """A convenience class for generating arbitrary length bit constants"""
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
