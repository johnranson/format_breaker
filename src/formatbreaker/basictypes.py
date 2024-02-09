"""This module contains formatbreaker.Parser subclasses that operate directly
on the bits and bytes of the data being parsed

If a Parser can be implemented as a subclass of an existing Parser
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
        """Reads a single byte from `addr` in `data` and stores the byte in an
        entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit or byte address in `data` where the byte to be parsed lies.

        Returns:
            The next bit or byte address after the parsed byte
        """
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
        """
        Args:
            byte_length:The length to read in bytes, when parsing.
            **kwargs: Arguments to be passed to the superclass constructor
        """
        util.validate_address_or_length(byte_length, 1)
        self._byte_length = byte_length
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        """Reads `self._byte_length` many bytes from `addr` in `data` and
        stores the bytes in an entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit or byte address in `data` where the bytes to be parsed lie.

        Returns:
            The next bit or byte address after the parsed bytes
        """
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
    """Reads a number of bytes from the data with length dynamically
    defined by another field in the data"""

    _backup_label = "VarBytes"

    def __init__(self, length_key: str, **kwargs: Any) -> None:
        """
        Args:
            length_key: The key to read from the context to get the number of
                bytes to read while parsing
            **kwargs: Arguments to be passed to the superclass constructor
        """
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
        """Reads `context[self.length_key]` many bytes from `addr` in `data`
        and stores the bytes in an entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit or byte address in `data` where the bytes to be parsed lie.

        Returns:
            The next bit or byte address after the parsed bytes
        """
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
    """Generates a spacer during parsing to a specific address"""

    def __call__(self, name: str | None = None, address: int | None = None) -> Parser:
        raise NotImplementedError

    def __init__(self, address: int) -> None:
        """
        Args:
            address: The address up to which to read
        """
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
        """Reads all data from `addr` to the end of `data` and stores the
        data in an entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit or byte address in `data` where the bytes to be parsed lie.

        Returns:
            The length of `data`
        """
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
        """Reads a single bit from `addr` in `data` and stores the bit in an
        entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit address in `data` where the byte to be parsed lies.

        Returns:
            The next bit address after the parsed byte
        """
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + 1

        if len(data) < end_addr:
            raise FBError("No bit available to parse Bit")

        result = data[addr]

        self._store(context, result, addr=addr)

        return end_addr


class BitWord(Parser):
    """Reads a number of bits from the data"""

    _bit_length: int
    _backup_label = "BitWord"

    def __init__(self, bit_length: int, **kwargs: Any) -> None:
        """
        Args:
            bit_length: The length to read in bits, when parsing.
            **kwargs: Arguments to be passed to the superclass constructor
        """
        util.validate_address_or_length(bit_length, 1)
        self._bit_length = bit_length
        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        """Reads `self._bit_length` many bits from `addr` in `data` and
        stores the bits as BitwiseBytes in an entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit address in `data` where the bytes to be parsed lie.

        Returns:
            The next bit address after the parsed bits
        """
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + self._bit_length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = data[addr:end_addr]

        self._store(context, result, addr=addr)

        return end_addr

    def _decode(self, data: util.BitwiseBytes) -> int:
        """Decodes the bits into an unsigned integer

        Args:
            data: A string of bits

        Returns:
            The bits converted to an unsigned integer
        """
        return int(data)
