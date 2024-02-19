"""This module contains formatbreaker.Parser subclasses that operate directly
on the bits and bytes of the data being parsed

If a Parser can be implemented as a subclass of an existing Parser
by only implementing __init__ and _decode, it should not go here.
"""

from __future__ import annotations
from typing import Any, override
import formatbreaker.core as fbc
import formatbreaker.util as fbu


class Byte(fbc.Parser):
    """Reads a single byte from the data"""

    _backup_label = "Byte"

    @override
    def _parse(self, data: fbu.DataSource, context: fbu.Context) -> None:
        """Reads a single byte from `addr` in `data` and stores the byte in an
        entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit or byte address in `data` where the byte to be parsed lies.
        """
        addr = data.current_address()
        result = data.read_bytes(1)
        self._store(context, result, addr)


class Bytes(fbc.Parser):
    """Reads a number of bytes from the data"""

    _backup_label = "Bytes"

    @override
    def __init__(self, byte_length: int, *args: Any, **kwargs: Any) -> None:
        """
        Args:
            byte_length:The length to read in bytes, when parsing.
            **kwargs: Arguments to be passed to the superclass constructor
        """
        fbu.validate_address_or_length(byte_length, 1)
        self._byte_length = byte_length
        super().__init__(*args, **kwargs)

    @override
    def _parse(self, data: fbu.DataSource, context: fbu.Context) -> None:
        """Reads `self._byte_length` many bytes from `addr` in `data` and
        stores the bytes in an entry in `context`

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the
                same containing Block
            addr: The bit or byte address in `data` where the bytes to be parsed lie.
        """

        addr = data.current_address()
        result = data.read_bytes(self._byte_length)
        self._store(context, result, addr)


class VarBytes(fbc.Parser):
    """Reads a number of bytes from the data with length dynamically
    defined by another field in the data"""

    _backup_label = "VarBytes"

    @override
    def __init__(self, *args: Any, source: str, **kwargs: Any) -> None:
        """
        Args:
            length_key: The key to read from the context to get the number of
                bytes to read while parsing
            **kwargs: Arguments to be passed to the superclass constructor
        """
        if not isinstance(source, str):
            raise TypeError
        self._length_key = source
        super().__init__(*args, **kwargs)

    @override
    def _parse(self, data: fbu.DataSource, context: fbu.Context) -> None:
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
        addr = data.current_address()
        length = context[self._length_key]
        result = data.read_bytes(length)
        self._store(context, result, addr)


class PadToAddress(fbc.Parser):
    """Generates a spacer during parsing to a specific address"""

    def __call__(
        self, name: str | None = None, address: int | None = None
    ) -> fbc.Parser:
        raise NotImplementedError

    @override
    def __init__(self, address: int) -> None:
        """
        Args:
            address: The address up to which to read
        """
        super().__init__(address=address)


class Remnant(fbc.Parser):
    """Reads all remainging bytes in the data"""

    _backup_label = "Remnant"

    @override
    def _parse(self, data: fbu.DataSource, context: fbu.Context) -> None:
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
        addr = data.current_address()
        result = data.read_bytes()

        self._store(context, result, addr)


class Bit(fbc.Parser):
    """Reads a single byte from the data"""

    _backup_label = "Bit"

    @override
    def _parse(self, data: fbu.DataSource, context: fbu.Context) -> None:
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
        addr = data.current_address()

        result = data.read_bits(1)

        self._store(context, result, addr)


class BitWord(fbc.Parser):
    """Reads a number of bits from the data"""

    _bit_length: int
    _backup_label = "BitWord"

    @override
    def __init__(self, bit_length: int, *args: Any, **kwargs: Any) -> None:
        """
        Args:
            bit_length: The length to read in bits, when parsing.
            **kwargs: Arguments to be passed to the superclass constructor
        """
        fbu.validate_address_or_length(bit_length, 1)
        self._bit_length = bit_length
        super().__init__(*args, **kwargs)

    @override
    def _parse(self, data: fbu.DataSource, context: fbu.Context) -> None:
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
        addr = data.current_address()
        result = data.read_bits(self._bit_length)
        self._store(context, result, addr=addr)

    @override
    def _decode(self, data: fbu.BitwiseBytes) -> int:
        """Decodes the bits into an unsigned integer

        Args:
            data: A string of bits

        Returns:
            The bits converted to an unsigned integer
        """
        return int(data)
