"""Extra formats that are useful"""

from uuid import UUID
from formatbreaker import Bytes


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
