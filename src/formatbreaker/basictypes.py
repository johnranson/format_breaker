from __future__ import annotations
from typing import Any
from formatbreaker.core import Parser, FBError
from formatbreaker import util


class Byte(Parser):
    """Reads a single byte from the data"""

    _backupname = "Byte"

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

    _backupname = "Bytes"

    def __init__(self, length: int, **kwargs: Any) -> None:
        util.validate_address_or_length(length, 1)
        self.length = length
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)

        length = self.length
        if bitwise:
            length = length * 8

        end_addr = addr + self.length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = bytes(data[addr:end_addr])

        self._store(context, result, addr=addr)

        return end_addr


class VarBytes(Parser):
    """Reads a number of bytes from the data with length defined by another
    field"""

    _backupname = "VarBytes"

    def __init__(self, length_key: str, **kwargs: Any) -> None:
        if not isinstance(length_key, str):
            raise TypeError
        self.length_key = length_key
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        bitwise = isinstance(data, util.BitwiseBytes)

        length = context[self.length_key]
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

    _backupname = "Remnant"

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

    _backupname = "Bit"

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

    _backupname = "BitFlags"

    def __init__(self, length: int, **kwargs: Any) -> None:

        util.validate_address_or_length(length, 1)
        self.length = length
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

        end_addr = addr + self.length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = data[addr:end_addr].to_bools()

        self._store(context, result, addr=addr)

        return end_addr


class BitWord(Parser):
    """Reads a number of bits from the data"""

    length: int
    _backupname = "BitWord"

    def __init__(self, length: int, **kwargs: Any) -> None:
        util.validate_address_or_length(length, 1)
        self.length = length
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

        end_addr = addr + self.length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = int(data[addr:end_addr])

        self._store(context, result, addr=addr)

        return end_addr
