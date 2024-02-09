"""This module contains Parsers that operate on the raw bit/bytestream

If a Parser can be implemented in a subclass of an existing Parser 
by only implementing __init__ and _decode, it should not go here.
"""

from __future__ import annotations
from typing import Any
from formatbreaker.core import Parser, FBError
from formatbreaker import util


class Byte(Parser):
    """Reads a single byte from the data"""

    _backup_label = "Byte"

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)
        if bitwise:
            length = 8
        else:
            length = 1
        end_addr = addr + length

        if len(data) < end_addr:
            raise FBError("No byte available to parse Byte")

        result = bytes(data[addr:end_addr])

        self._store(context, result, addr=addr)

        return end_addr


class Bytes(Parser):
    """Reads a number of bytes from the data"""

    _backup_label = "Bytes"

    def __init__(self, byte_length: int, **kwargs: Any) -> None:
        util.validate_address_or_length(byte_length, 1)
        self._byte_length = byte_length
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)

        length = self._byte_length
        if bitwise:
            length = length * 8

        end_addr = addr + self._byte_length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = bytes(data[addr:end_addr])

        self._store(context, result, addr=addr)

        return end_addr


class VarBytes(Parser):
    """Reads a number of bytes from the data with length defined by another
    field"""

    _backup_label = "VarBytes"

    def __init__(self, length_key: str, **kwargs: Any) -> None:
        if not isinstance(length_key, str):
            raise TypeError
        self._length_key = length_key
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)

        length = context[self._length_key]
        if bitwise:
            length = length * 8
        end_addr = addr + length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse VarBytes")

        result = bytes(data[addr:end_addr])

        self._store(context, result, addr=addr)

        return end_addr


class PadToAddress(Parser):
    """Brings the data stream to a specific address. Generates a spacer in the
    output. Does not have a name and
    """

    def __call__(
        self, name: str | None = None, address: int | None = None
    ) -> Parser:
        raise NotImplementedError

    def __init__(self, address: int) -> None:
        super().__init__(address=address)


class Remnant(Parser):
    """Reads all remainging bytes in the data"""

    _backup_label = "Remnant"

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        end_addr = len(data)

        result = bytes(data[addr:end_addr])

        self._store(context, result, addr=addr)

        return end_addr


class Bit(Parser):
    """Reads a single byte from the data"""

    _backup_label = "Bit"

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + 1

        if len(data) < end_addr:
            raise FBError("No bit available to parse Bit")

        result = data[addr]

        self._store(context, result, addr=addr)

        return end_addr


class BitFlags(Parser):
    """Reads a number of bits from the data"""

    _backup_label = "BitFlags"

    def __init__(self, bit_length: int, **kwargs: Any) -> None:

        util.validate_address_or_length(bit_length, 1)
        self._bit_length = bit_length
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + self._bit_length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = data[addr:end_addr].to_bools()

        self._store(context, result, addr=addr)

        return end_addr


class BitWord(Parser):
    """Reads a number of bits from the data"""

    _bit_length: int
    _backup_label = "BitWord"

    def __init__(self, bit_length: int, **kwargs: Any) -> None:
        util.validate_address_or_length(bit_length, 1)
        self._bit_length = bit_length
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + self._bit_length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = int(data[addr:end_addr])

        self._store(context, result, addr=addr)

        return end_addr
