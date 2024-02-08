"""This module contains the basic datatypes with no decoding"""

from __future__ import annotations
from typing import ClassVar, Any
from copy import copy
from formatbreaker import util


class FBError(Exception):
    """This error should be raised when a datatype fails to parse the data
    because it doesn't fit expectations. The idea is that optional data
    types can fail to be parsed, and the top level code will catch the
    exception and try something else.
    """


class DataType:
    """This is the base class for all objects that parse data"""

    name: str | None
    address: int | None
    backupname: ClassVar[str | None] = None

    def __init__(
        self, name: str | None = None, address: int | None = None
    ) -> None:
        """Basic code storing the name and address

        Args:
            name (string, optional): The key under which to store results in
                the context dictionary during parsing. Defaults to None.
            address (integer, optional): The address in the data which
                this instance should read from. Defaults to None.
        """
        if name is not None:
            if not isinstance(name, str):
                raise TypeError
        if address is not None:
            util.validate_address_or_length(address)

        self.address = address
        self.name = name


    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        """A method for parsing data provided at the address provided. This
            is data type dependent. Stores the parsed value in the context
            dictionary. Does nothing and returns the address unchanged by
            default. This should be overridden as needed by subclasses.

        Args:
            data (bytes or BitwiseBytes): Data to be parsed
            context (dict): The dictionary where results are stored
            addr (int): The bit or byte address to read from

        Returns:
            addr (int): The next bite or byte address after the parsed data
        """
        # pylint: disable=unused-argument
        util.validate_address_or_length(addr)
        return addr

    def _space_and_parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        """If the DataType has a fixed address, read to the address and save
            it as a spacer value in the context. Then call the _parse
            method.

        Args:
            data (bytes or BitwiseBytes): Data being parsed
            context (dict): The dictionary where results are stored
            addr (int): The current bit or byte address in the data

        Returns:
            addr (int): The next bite or byte address after the parsed data
        """
        util.validate_address_or_length(addr)
        if self.address:
            if addr > self.address:
                raise FBError("Target address has already been passed")
            if addr < self.address:
                spacer_size = self.address - addr
                addr = util.spacer(data, context, addr, spacer_size)
        return self._parse(data, context, addr)

    def parse(self, data: bytes | util.BitwiseBytes) -> dict[str, Any]:
        """Parse the provided data starting from address 0

        Args:
            data (bytes or BitwiseBytes): Data to be parsed

        Returns:
            dict: A dictionary of field names and parsed values
        """
        context: dict[str, Any] = {}
        self._space_and_parse(data, context, 0)
        return context

    def __call__(
        self, name: str | None = None, address: int | None = None
    ) -> DataType:
        """Allows instances to be callable to easily make a copy of the
            instance with a new name and/or address

        Args:
            name (string, optional): Replaces the name of the copied
                object if defined. Defaults to None.
            address (int, optional): Replaces the address of the copied
                object if defined. Defaults to None.

        Returns:
            DataType: A copy of the existing object with the name and address
                changed.
        """
        b = copy(self)
        if name is not None:
            if not isinstance(name, str):
                raise TypeError
            b.name = name
        if address is not None:
            util.validate_address_or_length(address)
            b.address = address
        return b

    def _store(
        self,
        context: dict[str, Any],
        data: Any,
        addr: int | None = None,
        name: str | None = None,
    ) -> None:
        """Decode the parsed data and store the value in a unique name

        Args:
            context (dict): Where to store the value
            data (object): The data to be decoded and stored
            name (string, optional): The name to store the data under. If no
                name is provided, the code will use the name stored in the
                instance. If no name is stored in the instance, it will default
                to the class backupname attribute.
            addr: The location the data came from, used for unnamed fields

        Raises:
            RuntimeError: If no name can be found, an exception is raised
        """

        if name:
            pass
        elif self.name:
            name = self.name
        elif self.backupname and (addr is not None):
            util.validate_address_or_length(addr)
            name = self.backupname + "_" + hex(addr)
        else:
            raise RuntimeError("Attempted to store unnamed data")

        name = util.uniquify_name(name, context)

        context[name] = self._decode(data)

    def _update(self, context: dict[str, Any], data: dict[str, Any]):
        """Decode a dictionary and store the new values in the provided
            dictionary

        Args:
            context (dict): Where to store the value
            data (dict): The data to be decoded and stored
        """

        decoded_data = self._decode(data)
        for key in decoded_data:
            self._store(context, decoded_data[key], name=key)

    def _decode(self, data: Any) -> Any:
        """A function for converting data to a different data type, run on the
            parsed output. Defaults to passing through the data unchanged.
            This should be overridden as needed by subclasses.

        Args:
            data (object): Input data

        Returns:
            object: Decoded output data
        """
        return data


class Chunk(DataType):
    """A container that holds ordered data fields and provides a mechanism for
    parsing them in order"""

    bitwise: bool
    relative: bool
    elements: tuple[DataType, ...]

    def __init__(
        self,
        *args: DataType,
        relative: bool = True,
        bitwise: bool = False,
        **kwargs: Any,
    ) -> None:
        """Holds any number of DataType elements and parses them in order.

        Args:
            *args (*DataType): Ordered list of the contained elements
            relative (bool, optional): True if addresses for the contained
                elements are relative to this chunk. Defaults to "true" if not
                defined.

        Raises:
            ValueError: one of the elements provided is not a DataType
        """
        if not isinstance(relative, bool):
            raise TypeError
        if not isinstance(bitwise, bool):
            raise TypeError
        if not isinstance(args, tuple):
            print(args)
            raise TypeError
        if not all(isinstance(item, DataType) for item in args):
            raise TypeError

        self.relative = relative
        self.bitwise = bitwise
        self.elements = args

        super().__init__(**kwargs)

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        """Parse the data using each element provided sequentially.

        Args:
            data (bytes or BitwiseBytes): Data being parsed
            context (dict): The dictionary where results are stored
            addr (int): The current bit or byte address in the data

        Returns:
            addr (int): The bite or byte address after the parsed data
        """
        util.validate_address_or_length(addr)

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
            if addr > len(data):
                raise RuntimeError

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
