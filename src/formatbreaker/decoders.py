"""Decoded formats"""

from __future__ import annotations
from typing import Any
import struct
from uuid import UUID
from formatbreaker.basictypes import Bit, BitWord, Bytes, Byte
from formatbreaker.core import FBError
from formatbreaker import util


class ByteFlag(Byte):
    """Reads 1 byte as a boolean"""

    _true_value: int | None
    _backup_label = "Flag"

    def __init__(
        self, true_value: bytes | int | None = None, **kwargs: Any
    ) -> None:

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

        super().__init__(**kwargs)

    def _decode(self, data: bytes) -> bool:
        if not data[0]:
            return False
        if self._true_value:
            if data[0] != self._true_value:
                raise FBError
        return True


class BitConst(Bit):

    _backup_label = "Const"

    def __init__(self, value: bool, **kwargs: Any) -> None:
        self._value = bool(value)
        super().__init__(**kwargs)

    def _decode(self, data: bool):
        return self._value == super()._decode(data)


class BitWordConst(BitWord):

    _backup_label = "Const"

    def __init__(
        self, value: bytes | util.BitwiseBytes, bit_length: int, **kwargs: Any
    ) -> None:

        self._value = int(util.BitwiseBytes(value, 0, bit_length))
        super().__init__(bit_length, **kwargs)

    def _decode(self, data: bool) -> bool:
        return self._value == super()._decode(data)


class Int32L(Bytes):

    _backup_label = "Int32"

    """Reads 4 bytes as a signed, little endian integer"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(4, **kwargs)

    def _decode(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=True)


class UInt32L(Bytes):

    _backup_label = "UInt32"

    """Reads 4 bytes as a unsigned, little endian integer"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(4, **kwargs)

    def _decode(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=False)


class Int16L(Bytes):

    _backup_label = "Int16"

    """Reads 2 bytes as a signed, little endian integer"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(2, **kwargs)

    def _decode(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=True)


class UInt16L(Bytes):

    _backup_label = "UInt16"

    """Reads 2 bytes as a unsigned, little endian integer"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(2, **kwargs)

    def _decode(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=False)


class Int8L(Byte):

    _backup_label = "Int8"

    """Reads 1 byte as a signed, little endian integer"""

    def _decode(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=True)


class UInt8(Byte):

    _backup_label = "UInt8"

    """Reads 1 byte as a unsigned, little endian integer"""

    def _decode(self, data: bytes) -> int:
        return int.from_bytes(data, "little", signed=False)


class Float32L(Bytes):
    """Reads 4 bytes as a little endian single precision float"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(4, **kwargs)

    def _decode(self, data: bytes) -> float:
        return struct.unpack("<f", data)[0]


class Float64L(Bytes):
    """Reads 8 bytes as a little endian double precision float"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(8, **kwargs)

    def _decode(self, data: bytes) -> float:
        return struct.unpack("<d", data)[0]


class UuidL(Bytes):
    """Reads 16 bytes as a UUID (Little Endian words)"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(16, **kwargs)

    def _decode(self, data: bytes) -> UUID:
        return UUID(bytes_le=data)


class UuidB(Bytes):
    """Reads 16 bytes as a UUID (Big Endian words)"""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(16, **kwargs)

    def _decode(self, data: bytes) -> UUID:
        return UUID(bytes=data)
