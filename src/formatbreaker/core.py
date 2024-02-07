"""This module contains the basic datatypes with no decoding"""

from formatbreaker import util


class FBError(Exception):
    """This error should be raised when a datatype fails to parse the data
    because it doesn't fit expectations. The idea is that optional data
    types can fail to be parsed, and the top level code will move on and try
    something else.
    """
    pass


class DataType():
    """This is the base class for all objects that parse data"""
    name: str
    address: int

    def __init__(self, name=None, address=None, copy_source=None) -> None:
        """Basic code storing the name and address

        Args:
            name (string, optional): The key under which to store results in
                the context dictionary during parsing. Defaults to None.
            address (integer, optional): The address in the data which
                this instance should read from. Defaults to None.
            copy_source (DataType, optional): An existing instance which
                should be copied
        """
        self.name = None
        self.address = None
        if copy_source:
            if not isinstance(copy_source, DataType):
                raise ValueError
            self.name = copy_source.name
            self.address = copy_source.address
        if name:
            if not isinstance(name, str):
                raise ValueError
            self.name = name
        if address is not None:
            if not isinstance(address, int):
                raise ValueError
            self.address = address

    def _parse(self, data, context, addr):
        """A method for parsing the current data at the current address. This
            is data type dependent. Stores the parsed value in the context
            dictionary.

        Args:
            data (bytes): Data being parsed
            context (dict): The dictionary where results are stored
            addr (int): The current byte address in the data

        Returns:
            addr (int): The  byte address after the parsed data
        """
        return addr


    def _space_and_parse(self, data, context, addr):
        """If the DataType has a fixed address, read to the address and save
            it as a spacer value in the context. Then call the _parse
            method.

        Args:
            data (bytes): Data being parsed
            context (dict): The dictionary where results are stored
            addr (int): The current address in the data

        Returns:
            addr (int): The address after the parsed data
        """
        if self.address:
            if addr > self.address:
                raise FBError("Target address has already been passed")
            if addr < self.address:
                spacer_size = self.address - addr
                addr = util.spacer(data, context, addr, spacer_size)
        return self._parse(data, context, addr)

    def parse(self, data):
        """Parse the provided bytes starting from address 0

        Args:
            data (bytes): Bytes to be parsed

        Returns:
            dict: A dictionary of field names and parsed values
        """
        context = {}
        self._space_and_parse(data, context, 0)
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
            context[util.uniquify_name(name, context)] = self._decode(data)
        elif self.name:
            context[util.uniquify_name(self.name, context)] = self._decode(data)
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
        self,
        *args,
        relative=None,
        name=None,
        address=None,
        copy_source=None,
        bitwise=None,
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
        self.bitwise = False
        self.relative = True
        self.elements = []
        if copy_source:
            self.bitwise = copy_source.bitwise
            self.relative = copy_source.relative
            self.elements = copy_source.elements
        if relative is not None:
            self.relative = relative
        if bitwise:
            self.bitwise = bitwise
        if args:
            self.elements = []
            for item in args:
                if isinstance(item, DataType):
                    self.elements.append(item)
                else:
                    raise ValueError
        super().__init__(name, address, copy_source)

    def _parse(self, data, context, addr):
        """Parse the data using each element provided sequentially.

        Args:
            data (bytes): Data being parsed
            context (dict): The dictionary where results are stored
            addr (int): The current byte address in the data

        Returns:
            addr (int): The  byte address after the parsed data
        """
        orig_addr = addr

        bitwisedata = isinstance(data, util.BitwiseBytes)

        if bitwisedata and not self.bitwise:
            raise ValueError

        convert_bit_addr_to_bytes = False
        if self.bitwise and not bitwisedata:
            convert_bit_addr_to_bytes = True
            data = util.BitwiseBytes(data[addr:])
            if not self.relative:
                raise RuntimeError

        elif self.relative:
            data = data[addr:]
            addr = 0

        out_context = {}

        for element in self.elements:
            addr = element._space_and_parse(data, out_context, addr)

        if convert_bit_addr_to_bytes:
            if addr % 8:
                raise RuntimeError
            addr = orig_addr + addr // 8

        elif self.relative:
            addr = orig_addr + addr

        if self.name:
            self._store(context, out_context)
        else:
            self._update(context, out_context)

        return addr
