"""Boolean and bitwise formats"""

from formatbreaker import Byte, FBException


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
                raise FBException
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
