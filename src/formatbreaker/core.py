"""This module contains the basic Parsers with no decoding"""

from __future__ import annotations
from typing import ClassVar, Any
from copy import copy
from formatbreaker import util


class FBError(Exception):
    """This error should be raised when a Parser fails to parse the data
    because it doesn't fit expectations. The idea is that optional data
    types can fail to be parsed, and the top level code will catch the
    exception and try something else.
    """


class Parser:
    """This is the base class for all objects that parse data"""

    __label: str | None
    __address: int | None
    _backup_label: ClassVar[str | None] = None

    @property
    def _label(self) -> str | None:
        return self.__label

    @_label.setter
    def _label(self, label: str | None) -> None:
        if label is not None and not isinstance(label, str):
            raise TypeError("Parser labels must be strings")
        self.__label = label

    @property
    def _address(self) -> int | None:
        return self.__address

    @_address.setter
    def _address(self, address: int | None) -> None:
        if address is not None:
            util.validate_address_or_length(address)
        self.__address = address

    def __init__(
        self, label: str | None = None, address: int | None = None
    ) -> None:
        """Constructor for Parser

        Parameters
        ----------
        label : str | None, default None
            The key under which to store results during parsing.
        address : int | None, default None
            The address in the data which this instance should read from.
        """
        self._address = address
        self._label = label

    def _parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        """Parses data into a dictionary

        Should be overridden by any subclass that reads data. Does
        nothing and returns `address` unchanged by default.

        Parameters
        ----------
        data : bytes | BitwiseBytes
            Data to be parsed
        context : dict[str, Any]
            Where the results are stored
        addr : int
            The bit or byte address in `data` where the data to be parse lies.

        Returns
        -------
        int
            The next bit or byte address after the parsed data
        """
        # pylint: disable=unused-argument
        util.validate_address_or_length(addr)
        if self._address is not None and self._address != addr:
            raise IndexError

        return addr

    def _space_and_parse(
        self,
        data: bytes | util.BitwiseBytes,
        context: dict[str, Any],
        addr: int,
    ) -> int:
        """Reads to the target location and then parses normally

        Parameters
        ----------
        data : bytes | BitwiseBytes
            Data to be parsed
        context : dict[str, Any]
            Where the results are stored
        addr : int
            The current bit or byte address in `data`

        Returns
        -------
        int
            The next bite or byte address after the parsed data

        Raises
        ------
        FBError
            The current address in `data` is past the `self.address`
        """
        util.validate_address_or_length(addr)
        if self._address:
            if addr > self._address:
                raise FBError("Target address has already been passed")
            if addr < self._address:
                addr = util.spacer(data, context, addr, self.__address)
        return self._parse(data, context, addr)

    def parse(self, data: bytes | util.BitwiseBytes) -> dict[str, Any]:
        """Parse the provided data from the beginning

        Parameters
        ----------
        data : bytes | util.BitwiseBytes
            Data to be parsed

        Returns
        -------
        dict[str, Any]
            A dictionary of field labels and parsed values
        """
        context: dict[str, Any] = {}
        self._space_and_parse(data, context, 0)
        return context

    def __call__(
        self, label: str | None = None, address: int | None = None
    ) -> Parser:
        """Copy the current instance with a new label or address

        Parameters
        ----------
        label : str | None, optional
            Replacement label, if defined
        address : int | None, optional
            Replacement address, if defined

        Returns
        -------
        Parser
            A copy of the existing object with the label and address changed.
        """

        b = copy(self)
        if label is not None:
            b._label = label
        if address is not None:
            b._address = address
        return b

    def _store(
        self,
        context: dict[str, Any],
        data: Any,
        addr: int | None = None,
        label: str | None = None,
    ) -> None:
        """Decode the parsed data and store the value with a unique key
        
        If `label` is not provided, the code will use self.`label`. If
        `self.label` is None, it will default to the class `_backup_label`
        attribute.

        Parameters
        ----------
        context : dict[str, Any]
            Where the results are stored
        data : Any
            The data to be decoded and stored
        addr : int | None, optional
            The location the data came from, used for unlabeled fields
        label : str | None, optional
            The label to store the data under.
        """        


        if label:
            pass
        elif self._label:
            label = self._label
        elif self._backup_label:
            if addr is not None:
                util.validate_address_or_length(addr)
                label = self._backup_label + "_" + hex(addr)
            else:
                label = self._backup_label
        else:
            raise RuntimeError("Attempted to store unlabeled data")

        label = util.uniquify_label(label, context)

        context[label] = self._decode(data)

    def _update(self, context: dict[str, Any], data: dict[str, Any]):
        """Decode a dictionary and update into another dictionary

        Parameters
        ----------
        context : dict[str, Any]
            Where to store the results
        data : dict[str, Any]
            The data to be decoded and stored
        """        
        decoded_data = self._decode(data)
        for key in decoded_data:
            self._store(context, decoded_data[key], label=key)

    def _decode(self, data: Any) -> Any:
        """Converts parsed data to another format
        
        Defaults to passing through the data unchanged.
        This should be overridden as needed by subclasses.
        
        Parameters
        ----------
        data : Any
            Input data from parsing and previous decoding steps

        Returns
        -------
        Any
            Decoded output data
        """
        return data


class Block(Parser):
    """A container that holds ordered data fields and provides a mechanism for
    parsing them in order"""

    bitwise: bool
    relative: bool
    elements: tuple[Parser, ...]

    def __init__(
        self,
        *args: Parser,
        relative: bool = True,
        bitwise: bool = False,
        **kwargs: Any,
    ) -> None:
        """Constructs a Block

        Parameters
        ----------
        *args : tuple[Parser, ...]
            Ordered tuple of the Parsers this Block should hold
        relative : bool, default True
            If True, addresses for `self.elements` are relative to this Block.
        bitwise : bool, default False
            If True, `self.elements` is addressed and parsed bitwise
        **kwargs : dict[str, Any]
            Arguments to be passed to the superclass constructor
        """        
        if not isinstance(relative, bool):
            raise TypeError
        if not isinstance(bitwise, bool):
            raise TypeError
        if not isinstance(args, tuple):
            raise TypeError
        if not all(isinstance(item, Parser) for item in args):
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
        """Parse the data using each Parser sequentially.

        Parameters
        ----------
        data : bytes | BitwiseBytes
            Data to be parsed
        context : dict[str, Any]
            Where the results are stored
        addr : int
            The bit or byte address in `data` where the data to be parse lies.

        Returns
        -------
        int
            The next bit or byte address after the parsed data
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

        if self._label:
            self._store(context, out_context)
        else:
            self._update(context, out_context)

        return addr
