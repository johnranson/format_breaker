"""Decoded formats"""

import struct
from uuid import UUID
from formatbreaker.basictypes import Bit, BitWord, Bytes, Byte
from formatbreaker.core import FBError
from formatbreaker import util


class ByteFlag(Byte):
    """Reads 1 byte as a boolean"""

    def __init__(self, value=None, name=None, address=None, copy_source=None) -> None:
        if copy_source:
            self.value = copy_source.value
        if value:
            self.length_key = value
        super().__init__(name, address, copy_source)

    def _decode(self, data):
        if not data[0]:
            return False
        if self.value:
            if data[0] != self.value:
                raise FBError
        return True


class BitConst(Bit):
    def __init__(self, value=None, name=None, address=None, copy_source=None) -> None:
        if copy_source:
            self.value = copy_source.value
        self.value = bool(value)
        super().__init__(name, address, copy_source)

    def _decode(self, data):
        return self.value == super()._decode(data)


class BitWordConst(BitWord):
    def __init__(
        self, value=None, length=None, name=None, address=None, copy_source=None
    ) -> None:
        self.length = 1
        if copy_source:
            self.value = copy_source.value

        if value is not None:
            if not length:
                raise ValueError
            else:
                self.value = int(util.BitwiseBytes(value, 0, 0, length))
        super().__init__(length, name, address, copy_source)

    def _decode(self, data):
        return self.value == super()._decode(data)


class Int32sl(Bytes):
    """Reads 4 bytes as a signed, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(4, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(data, "little", signed=True)


class Int32ul(Bytes):
    """Reads 4 bytes as a unsigned, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(4, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(data, "little", signed=False)


class Int16sl(Bytes):
    """Reads 2 bytes as a signed, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(2, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(data, "little", signed=True)


class Int16ul(Bytes):
    """Reads 2 bytes as a unsigned, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(2, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(data, "little", signed=False)


class Int8sl(Byte):
    """Reads 1 byte as a signed, little endian integer"""

    def _decode(self, data):
        return int.from_bytes(data, "little", signed=True)


class Int8ul(Byte):
    """Reads 1 byte as a unsigned, little endian integer"""

    def _decode(self, data):
        return int.from_bytes(data, "little", signed=False)


class Float32l(Bytes):
    """Reads 4 bytes as a little endian single precision float"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(4, name, address, copy_source)

    def _decode(self, data):
        return struct.unpack("<f", data)[0]


class Float64l(Bytes):
    """Reads 8 bytes as a little endian double precision float"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(8, name, address, copy_source)

    def _decode(self, data):
        return struct.unpack("<d", data)[0]


class uuid_le(Bytes):
    """Reads 16 bytes as a UUID (Little Endian words)"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(16, name, address, copy_source)

    def _decode(self, data):
        return UUID(bytes_le=data)


class uuid_be(Bytes):
    """Reads 16 bytes as a UUID (Big Endian words)"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(16, name, address, copy_source)

    def _decode(self, data):
        return UUID(bytes=data)
