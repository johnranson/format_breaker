from abc import ABC, abstractmethod
import struct

class FBException(Exception):
    pass


def uniquify_name(name, context):
    """This adds " N" to a string key if the key already exists in the
        dictionary, where N is the first natural number that makes the
        key unique

    Args:
        name (string): A string
        context (dictionary): Any dictionary

    Returns:
        string: A unique string key
    """
    new_name = name
    i = 1
    while new_name in context:
        new_name = name + " " + str(i)
        i = i + 1
    return new_name


def spacer(data, context, abs_addr, rel_addr, spacer_size):
    """Reads a spacer of a certain length from the data, and saves it
        to the context dictionary

    Args:
        data (bytes): Data being parsed
        context (dict): The dictionary where results are stored
        abs_addr (int): The current absolute byte address in the data
        rel_addr (int): The current relative byte address in the
            current data chunk
        spacer_size (_type_): The size in bytes of the spacer

    Returns:
        abs_addr (int): The absolute byte address following the spacer
        rel_addr (int): The relative byte address in the
            current data chunk following the spacer
    """
    end_abs_addr = abs_addr + spacer_size
    end_rel_addr = rel_addr + spacer_size

    if spacer_size > 1:
        spacer_name = "spacer_" + hex(rel_addr) + "-" + hex(end_rel_addr - 1)
    else:
        spacer_name = "spacer_" + hex(rel_addr)

    spacer_name = uniquify_name(spacer_name, context)

    context[spacer_name] = data[abs_addr:end_abs_addr]

    return end_abs_addr, end_rel_addr


class DataType(ABC):
    """This is the base class for all objects that parse data"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        """Basic code storing the name and address

        Args:
            name (string, optional): The key under which to store results in
                the context dictionary during parsing. Defaults to None.
            address (integer, optional): The address in the data array which
                this instance should read from. Defaults to None.
            copy_source (DataType, optional): An existing instance which
                should be copied
        """
        self.name = None
        self.address = None
        if copy_source:
            self.name = copy_source.name
            self.address = copy_source.address
        if name:
            self.name = name
        if address:
            self.address = address

    @abstractmethod
    def _parse(self, data, context, abs_addr, rel_addr):
        """A method for parsing the current data at the current address. This
            is data type dependent. Stores the parsed value in the context
            dictionary.

        Args:
            data (bytes): Data being parsed
            context (dict): The dictionary where results are stored
            abs_addr (int): The current absolute byte address in the data
            rel_addr (int): The current relative byte address in the
            current data chunk

        Returns:
            abs_addr (int): The absolute byte address after the parsed data
            rel_addr (int): The relative byte address in the
            current data chunk after the parsed data
        """

    def _space_and_parse(self, data, context, abs_addr, rel_addr):
        """If the DataType has a fixed address, read to the address and save
            it as a spacer value in the context. Then call the _parse
            method.

        Args:
            data (bytes): Bytes to be parsed
            context (dict): The dictionary where results are stored
            abs_addr (int): The current absolute byte address in the data
            rel_addr (int): The current relative byte address in the
            current data chunk

        Returns:
            abs_addr (int): The absolute byte address after the parsed data
            rel_addr (int): The relative byte address in the
            current data chunk after the parsed data
        """
        if self.address:
            if rel_addr > self.address:
                raise FBException("Target address has already been passed")
            if rel_addr < self.address:
                spacer_size = self.address - rel_addr
                abs_addr, rel_addr = spacer(
                    data, context, abs_addr, rel_addr, spacer_size
                )
        return self._parse(data, context, abs_addr, rel_addr)

    def parse(self, data):
        """Parse the provided bytes starting from address 0

        Args:
            data (bytes): Bytes to be parsed

        Returns:
            dict: A dictionary of field names and parsed values
        """
        context = {}
        self._space_and_parse(data, context, 0, 0)
        return context

    def __call__(self, new_name=None, new_address=None):
        """Allows instances to be callable to easily copy an instance with a
            new name and/or address

        Args:
            new_name (string, optional): Replaces the name of the copied
                object if defined. Defaults to None.
            new_address (int, optional): Replaces the address of the copied
                object if defined. Defaults to None.

        Returns:
            DataType: A copy of the existing object with the name and address
                changed.
        """
        name = new_name if new_name else self.name
        address = new_address if new_address else self.address
        return type(self)(name=name, address=address, copy_source=self)

    def _store(self, context, data, name=None):
        """Decode the parsed data and store the value in a unique name

        Args:
            context (dict): Where to store the value
            data (object): The data to be decoded and stored
            name (string, optional): The name to store the data under. If no
                name is provided, the code will use the name stored in the
                instance. Defaults to None.

        Raises:
            RuntimeError: If no name can be found, an exception is raised
        """
        if name:
            context[uniquify_name(name, context)] = self._decode(data)
        elif self.name:
            context[uniquify_name(self.name, context)] = self._decode(data)
        else:
            raise RuntimeError("Attempted to store unnamed data")

    def _update(self, context, data):
        """Decode a dictionary and store the new values in the provided
            dictionary

        Args:
            context (dict): Where to store the value
            data (dict): The data to be decoded and stored

        Raises:
            RuntimeError: If no name can be found, an exception is raised
        """

        decoded_data = self._decode(data)
        for key in decoded_data:
            self._store(context, decoded_data[key], key)

    def _decode(self, data):
        """A function for converting data to a different data type, run on the
            parsed output. Defaults to passing through the data unchanged

        Args:
            data (object): Input data

        Returns:
            object: Decoded output data
        """
        return data


class Chunk(DataType):
    """A container that holds ordered data fields and provides a mechanism for parsing them in order"""

    def __init__(
        self, *args, relative=None, name=None, address=None, copy_source=None
    ) -> None:
        """Holds any number of DataType elements and parses them in order.

        Args:
            *args (*DataType): Ordered list of the contained elements
            relative (bool, optional): True if addresses for the contained
                elements are relative to this chunk. Defaults to "true" if not
                defined.
            name (string, optional): Key where the decoded data is stored.
                If not defined, decoded parsed data is stored directly in the
                parsing context
            address (integer, optional): The address in the data array which
                this instance should read from. Defaults to None.
            copy_source (DataType, optional): An existing instance which
                should be copied

        Raises:
            ValueError: one of the elements provided is not a DataType
        """
        self.relative = True
        self.args = []
        if copy_source:
            self.relative = copy_source.relative
            self.elements = copy_source.elements
        if relative is not None:
            self.relative = relative
        if args:
            self.data_list = []
            for item in args:
                if isinstance(item, DataType):
                    self.elements.append(item)
                else:
                    raise ValueError
        super().__init__(name, address, copy_source)

    def _parse(self, data, context, abs_addr, rel_addr):
        """Parse the data using each element provided sequentially.

        Args:
            data (bytes): Data being parsed
            context (dict): The dictionary where results are stored
            abs_addr (int): The current absolute byte address in the data
            rel_addr (int): The current relative byte address in the
            current data chunk

        Returns:
            abs_addr (int): The absolute byte address after the parsed data
            rel_addr (int): The relative byte address in the current data
                chunk after the parsed data
        """
        orig_abs_addr = abs_addr
        orig_rel_addr = rel_addr
        if self.relative:
            rel_addr = 0
        out_context = {}
        for element in self.elements:
            abs_addr, rel_addr = element._space_and_parse(
                data, out_context, abs_addr, rel_addr
            )
        chunk_size = abs_addr - orig_abs_addr
        rel_addr = chunk_size + orig_rel_addr
        if self.name:
            self._store(context, out_context)
        else:
            self._update(context, out_context)
        return abs_addr, rel_addr


class Byte(DataType):
    """Reads a single byte from the data"""

    def _parse(self, data, context, abs_addr, rel_addr):
        if len(data) < abs_addr + 1:
            raise FBException("No byte available to parse Byte")

        end_abs_addr = abs_addr + 1
        end_rel_addr = rel_addr + 1

        if self.name:
            self._store(context, data[abs_addr:end_abs_addr])
        else:
            byte_name = "byte_" + hex(rel_addr)
            self._store(context, data[abs_addr:end_rel_addr], byte_name)

        return end_abs_addr, end_rel_addr


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

    def _parse(self, data, context, abs_addr, rel_addr):
        if len(data) < abs_addr + self.length:
            raise FBException("Insufficient bytes available to parse Bytes")
        end_abs_addr = abs_addr + self.length
        end_rel_addr = rel_addr + self.length

        if self.name:
            self._store(context, data[abs_addr:end_abs_addr])
        else:
            bytes_name = "bytes_" + hex(rel_addr)
            self._store(context, data[abs_addr:end_abs_addr], bytes_name)

        return end_abs_addr, end_rel_addr


class VarBytes(DataType):
    """Reads a number of bytes from the data with length defined by another field"""

    def __init__(
        self, name=None, address=None, length_key=None, copy_source=None
    ) -> None:
        if copy_source:
            self.lengh_key = copy_source.length_key
        if length_key:
            self.length_key = length_key
        super().__init__(name, address, copy_source)

    def _parse(self, data, context, abs_addr, rel_addr):

        length = context[self.length_key]
        if len(data) < abs_addr + length:
            raise FBException("Insufficient bytes available to parse VarBytes")

        end_abs_addr = abs_addr + length
        end_rel_addr = rel_addr + length

        if self.name:
            self._store(context, data[abs_addr:end_abs_addr])
        else:
            bytes_name = "bytes_" + hex(rel_addr)
            self._store(context, data[abs_addr:end_abs_addr], bytes_name)

        return end_abs_addr, end_rel_addr


class PadToAddress(DataType):
    """Brings the data stream to a specific address. Generates a spacer in the
    output
    """

    def __init__(self, address) -> None:
        super().__init__(address=address)

    def _parse(self, data, context, abs_addr, rel_addr):
        return abs_addr, rel_addr


class Remnant(DataType):
    """Reads all remainging bytes in the data"""

    def _parse(self, data, context, abs_addr, rel_addr):
        length = len(data) - abs_addr

        end_abs_addr = abs_addr + length
        end_rel_addr = rel_addr + length

        if self.name:
            self._store(context, data[abs_addr:end_abs_addr])
        else:
            rem_name = "remnant_" + hex(rel_addr)
            self._store(context, data[abs_addr:end_abs_addr], rem_name)

        return end_abs_addr, end_rel_addr


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

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(name, address, copy_source)

    def _decode(self, data):
        return int.from_bytes(super()._decode(data), "little", signed=True)


class Int8ul(Byte):
    """Reads 1 byte as a unsigned, little endian integer"""

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        super().__init__(name, address, copy_source)

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
