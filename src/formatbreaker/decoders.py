"""Decoding Parsers

The classes in this module add functionality to existing parsers by adding
`_decode()` logic. They only implement _decode (and _init, if needed.)
"""

from __future__ import annotations
from typing import Any, override
import struct
import uuid
import formatbreaker.basictypes as fbb
import formatbreaker.util as fbu


class ByteFlag(fbb.Byte):
    """Reads 1 byte as a boolean"""

    _true_value: int | None
    _backup_label = "Flag"

    @override
    def __init__(self, true_value: bytes | int | None = None, **kwargs: Any) -> None:
        """
        Args:
            true_value: The only value which the parser will interpret as True, if
                defined.
            **kwargs: Arguments to be passed to the superclass constructor
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

        super().__init__(**kwargs)

    @override
    def _decode(self, data: bytes) -> bool:
        if not data[0]:
            return False
        if self._true_value:
            if data[0] != self._true_value:
                raise fbu.FBError("Value to decode is not '0' or self._true_value")
        return True


class BitConst(fbb.Bit):
    """Fails parsing if a bit doesn't match a constant value"""

    _backup_label = "Const"

    @override
    def __init__(self, value: bool, **kwargs: Any) -> None:
        self._value = bool(value)
        super().__init__(**kwargs)

    @override
    def _decode(self, data: bool) -> bool:
        if self._value != super()._decode(data):
            raise fbu.FBError("Constant not matched")
        return self._value


class BitWordConst(fbb.BitWord):
    """Fails parsing if a word doesn't match a constant value"""

    _backup_label = "Const"

    @override
    def __init__(
        self, value: bytes | fbu.BitwiseBytes, bit_length: int, **kwargs: Any
    ) -> None:

        self._value = fbu.BitwiseBytes(value, 0, bit_length)
        super().__init__(bit_length, **kwargs)

    @override
    def _decode(self, data: fbu.BitwiseBytes) -> int:
        if self._value != data:
            raise fbu.FBError("Constant not matched")
        return int(self._value)


class BitFlags(fbb.BitWord):
    """Reads a number of bits from the data"""

    _backup_label = "Const"

    @override
    def _decode(self, data: fbu.BitwiseBytes) -> list[bool]:
        return data.to_bools()


class Int32L(fbb.Bytes):
    """Reads 4 bytes as a signed, little endian integer"""

    _backup_label = "Int32"

    @override
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(4, **kwargs)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a signed integer from 4 little endian bytes.

        Args:
            data: Four little endian bytes encoding an signed integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=True)


class UInt32L(fbb.Bytes):
    """Reads 4 bytes as a unsigned, little endian integer"""

    _backup_label = "UInt32"

    @override
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(4, **kwargs)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a unsigned integer from 4 little endian bytes.

        Args:
            data: Four little endian bytes encoding an unsigned integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=False)


class Int16L(fbb.Bytes):
    """Reads 2 bytes as a signed, little endian integer"""

    _backup_label = "Int16"

    @override
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(2, **kwargs)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a signed integer from 2 little endian bytes.

        Args:
            data: Two little endian bytes encoding an signed integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=True)


class UInt16L(fbb.Bytes):
    """Reads 2 bytes as a unsigned, little endian integer"""

    _backup_label = "UInt16"

    @override
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(2, **kwargs)

    @override
    def _decode(self, data: bytes) -> int:
        """Decodes a unsigned integer from 2 little endian bytes.

        Args:
            data: Two little endian bytes encoding an unsigned integer

        Returns:
            The decoded number
        """
        return int.from_bytes(data, "little", signed=False)


class Int8(fbb.Byte):
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


class UInt8(fbb.Byte):
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


class Float32L(fbb.Bytes):
    """Reads 4 bytes as a little endian single precision float"""

    _backup_label = "Float32"

    @override
    def __init__(self, **kwargs: Any) -> None:
        """Decodes a single precision floating point number from little endian
        bytes.

        Args:
            data: 4 little endian bytes encoding a single precision floating point
                number

        Returns:
            The decoded number
        """

        super().__init__(4, **kwargs)

    @override
    def _decode(self, data: bytes) -> float:
        return struct.unpack("<f", data)[0]


class Float64L(fbb.Bytes):
    """Reads 8 bytes as a little endian double precision float"""

    _backup_label = "Float64"

    @override
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(8, **kwargs)

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


class UuidL(fbb.Bytes):
    """Reads 16 bytes as a UUID (Little Endian words)"""

    _backup_label = "UUID"

    @override
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(16, **kwargs)

    @override
    def _decode(self, data: bytes) -> uuid.UUID:
        """Decodes a UUID with little endian words.

        Args:
            data: A 16 byte binary UUID with little endian words

        Returns:
            The decoded UUID
        """
        return uuid.UUID(bytes_le=data)


class UuidB(fbb.Bytes):
    """Reads 16 bytes as a UUID (Big Endian words)"""

    _backup_label = "UUID"

    @override
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(16, **kwargs)

    @override
    def _decode(self, data: bytes) -> uuid.UUID:
        """Decodes a UUID with big endian words.

        Args:
            data: A 16 byte binary UUID with big endian words

        Returns:
            The decoded UUID
        """
        return uuid.UUID(bytes=data)
