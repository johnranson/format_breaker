from formatbreaker.core import DataType, FBError
from formatbreaker import util


class Byte(DataType):
    """Reads a single byte from the data"""

    def _parse(self, data, context, addr):
        bitwise = isinstance(data, util.BitwiseBytes)
        if bitwise:
            length = 8
        else:
            length = 1
        end_addr = addr + length

        if len(data) < end_addr:
            raise FBError("No byte available to parse Byte")

        result = bytes(data[addr:end_addr])

        if self.name:
            self._store(context, result)
        else:
            byte_name = "byte_" + hex(addr)
            self._store(context, result, byte_name)

        return end_addr


class Bytes(DataType):
    """Reads a number of bytes from the data"""

    def __init__(self, length=None, name=None, address=None, copy_source=None) -> None:
        if copy_source:
            self.length = copy_source.length
        if length:
            if not isinstance(length, int):
                raise ValueError
            if length < 1:
                raise ValueError
            self.length = length
        super().__init__(name, address, copy_source)

    def _parse(self, data, context, addr):
        bitwise = isinstance(data, util.BitwiseBytes)

        length = self.length
        if bitwise:
            length = length * 8

        end_addr = addr + self.length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = bytes(data[addr:end_addr])

        if self.name:
            self._store(context, result)
        else:
            bytes_name = "bytes_" + hex(addr)
            self._store(context, result, bytes_name)

        return end_addr


class VarBytes(DataType):
    """Reads a number of bytes from the data with length defined by another field"""

    def __init__(
        self, name=None, address=None, length_key=None, copy_source=None
    ) -> None:
        if copy_source:
            self.length_key = copy_source.length_key
        if length_key:
            self.length_key = length_key
        super().__init__(name, address, copy_source)

    def _parse(self, data, context, addr):
        bitwise = isinstance(data, util.BitwiseBytes)

        length = context[self.length_key]
        if bitwise:
            length = length * 8
        end_addr = addr + length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse VarBytes")

        result = bytes(data[addr:end_addr])

        if self.name:
            self._store(context, result)
        else:
            bytes_name = "bytes_" + hex(addr)
            self._store(context, result, bytes_name)

        return end_addr


class PadToAddress(DataType):
    """Brings the data stream to a specific address. Generates a spacer in the
    output. Does not have a name and 
    """
    __call__ = None

    def __init__(self, address) -> None:
        super().__init__(address=address)


class Remnant(DataType):
    """Reads all remainging bytes in the data"""

    def _parse(self, data, context, addr):
        end_addr = len(data)

        result = bytes(data[addr:end_addr])

        if self.name:
            self._store(context, result)
        else:
            rem_name = "remnant_" + hex(addr)
            self._store(context, result, rem_name)

        return end_addr


class Bit(DataType):
    """Reads a single byte from the data"""

    def _parse(self, data, context, addr):
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + 1

        if len(data) < end_addr:
            raise FBError("No bit available to parse Bit")

        result = data[addr]

        if self.name:
            self._store(context, result)
        else:
            bit_name = "bit_" + hex(addr)
            self._store(context, result, bit_name)

        return end_addr


class BitFlags(DataType):
    """Reads a number of bits from the data"""

    def __init__(self, length=None, name=None, address=None, copy_source=None) -> None:
        if copy_source:
            self.length = copy_source.length
        if length:
            if not isinstance(length, int):
                raise ValueError
            if length < 1:
                raise ValueError
            self.length = length
        super().__init__(name, address, copy_source)

    def _parse(self, data, context, addr):
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + self.length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = data[addr:end_addr].to_bools()

        if self.name:
            self._store(context, result)
        else:
            bytes_name = "bits_" + hex(addr)
            self._store(context, result, bytes_name)

        return end_addr


class BitWord(DataType):
    """Reads a number of bits from the data"""

    def __init__(self, length=None, name=None, address=None, copy_source=None) -> None:
        if copy_source:
            self.length = copy_source.length
        if length:
            if not isinstance(length, int):
                raise ValueError
            if length < 1:
                raise ValueError
            self.length = length
        super().__init__(name, address, copy_source)

    def _parse(self, data, context, addr):
        bitwise = isinstance(data, util.BitwiseBytes)
        if not bitwise:
            raise RuntimeError

        end_addr = addr + self.length

        if len(data) < end_addr:
            raise FBError("Insufficient bytes available to parse Bytes")

        result = int(data[addr:end_addr])

        if self.name:
            self._store(context, result)
        else:
            bytes_name = "bits_" + hex(addr)
            self._store(context, result, bytes_name)

        return end_addr
