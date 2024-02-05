"""This module contains the datatypes which decode as numbers"""

import struct
from formatbreaker.core import Bytes, Byte


class Int32sl(Bytes):
    """Reads 4 bytes as a signed, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(4, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(super()._decode(data), "little", signed=True)


class Int32ul(Bytes):
    """Reads 4 bytes as a unsigned, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(4, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(super()._decode(data), "little", signed=False)


class Int16sl(Bytes):
    """Reads 2 bytes as a signed, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(2, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(super()._decode(data), "little", signed=True)


class Int16ul(Bytes):
    """Reads 2 bytes as a unsigned, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(2, name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(super()._decode(data), "little", signed=False)


class Int8sl(Byte):
    """Reads 1 byte as a signed, little endian integer"""

    def _decode(self, data):
        return int.from_bytes(super()._decode(data), "little", signed=True)


class Int8ul(Byte):
    """Reads 1 byte as a unsigned, little endian integer"""

    def _decode(self, data):
        return int.from_bytes(super()._decode(data), "little", signed=False)


class Float32l(Bytes):
    """Reads 4 bytes as a little endian single precision float"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(4, name, address, copy_source)

    def _decode(self, data):
        return struct.unpack("<f", super()._decode(data))[0]


class Float64l(Bytes):
    """Reads 8 bytes as a little endian double precision float"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(8, name, address, copy_source)

    def _decode(self, data):
        return struct.unpack("<d", super()._decode(data))[0]
