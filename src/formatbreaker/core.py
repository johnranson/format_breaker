"""This module contains the basic Parser and Block (Parser container) code"""

from __future__ import annotations
from typing import ClassVar, Any, override
import copy
import io
import formatbreaker.util as fbu
import formatbreaker.datasource as ds
import collections


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
            fbu.validate_address_or_length(address)
        self.__address = address

    def __init__(self, label: str | None = None, address: int | None = None) -> None:
        """
        Args:
            label:The key under which to store results during parsing.
            address: The address in the data which this instance should read from.
        """
        self._address = address
        self._label = label

    def _parse(self, data: ds.DataSource, context: Context) -> None:
        """Parses data into a dictionary

        Should be overridden by any subclass that reads data. Does
        nothing and returns `address` unchanged by default.

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the same
                containing Block
        """
        # pylint: disable=unused-argument

    def _space_and_parse(self, data: ds.DataSource, context: Context) -> None:
        """Reads to the target location and then parses normally

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the same
                containing Block
        """
        if self._address is not None:
            _spacer(data, context, self._address)
        self._parse(data, context)

    def parse(self, data: bytes | io.BufferedIOBase) -> dict:
        """Parse the provided data from the beginning

        Args:
            data: Data being parsed

        Returns:
            A dictionary of field labels and parsed values
        """
        context = Context()
        with ds.DataSource(src=data) as datasource:
            self._space_and_parse(datasource, context)
        return dict(context)

    def __call__(self, label: str | None = None, address: int | None = None) -> Parser:
        """Copy the current instance with a new label or address

        Args:
            label: Replacement label, if defined
            address: Replacement address, if defined

        Returns:
            A copy of the existing object with the label and address changed.
        """

        b = copy.copy(self)
        if label is not None:
            b._label = label
        if address is not None:
            b._address = address
        return b

    def _store(
        self,
        context: Context,
        data: Any,
        addr: int | None = None,
        label: str | None = None,
    ) -> None:
        """Decode the parsed data and store the value with a unique key

        If `label` is not provided, the code will use `self._label`. If
        `self._label` is None, it will default to the class `_backup_label`
        attribute.

        Args:
            context: Where results are stored including prior results in the same
                containing Block
            data: The data to be decoded and stored
            addr: The location the data came from, used for unlabeled fields
            label: The label to store the data under.
        """

        if label:
            pass
        elif self._label:
            label = self._label
        elif self._backup_label:
            if addr is not None:
                fbu.validate_address_or_length(addr)
                label = self._backup_label + "_" + hex(addr)
            else:
                label = self._backup_label
        else:
            raise RuntimeError("Attempted to store unlabeled data")

        context[label] = self._decode(data)

    def _update(self, context: Context, data: Context):
        """Decode a dictionary and update into another dictionary

        Args:
            context: Where to store the results
            data: The data to be decoded and stored
        """
        decoded_data = self._decode(data)
        for key in decoded_data:
            self._store(context, decoded_data[key], label=key)

    def _decode(self, data: Any) -> Any:
        """Converts parsed data to another format

        Defaults to passing through the data unchanged.
        This should be overridden as needed by subclasses.

        Args:
            data: Input data from parsing and previous decoding steps

        Returns:
            Decoded output data
        """
        return data


class Block(Parser):
    """A container that holds ordered data fields and provides a mechanism for
    parsing them in order"""

    _addr_type: ds.AddrType
    _relative: bool
    _elements: tuple[Parser, ...]
    _optional: bool

    def __init__(
        self,
        *args: Parser,
        relative: bool = True,
        addr_type: ds.AddrType | str = ds.AddrType.PARENT,
        optional: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            *args: Ordered tuple of the Parsers this Block should hold
            relative: If True, addresses for `self.elements` are relative to this Block.
            bitwise: If True, `self.elements` is addressed and parsed bitwise
            **kwargs: Arguments to be passed to the superclass constructor
        """
        if not isinstance(relative, bool):
            raise TypeError
        if not all(isinstance(item, Parser) for item in args):
            raise TypeError
        if isinstance(addr_type, ds.AddrType):
            self._addr_type = addr_type
        else:
            self._addr_type = ds.AddrType[addr_type]

        self._relative = relative
        self._optional = optional
        self._elements = args

        super().__init__(**kwargs)

    @override
    def _parse(
        self,
        data: ds.DataSource,
        context: Context,
    ) -> None:
        """Parse the data using each Parser sequentially.

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the same
                containing Block
            addr: The bit or byte address in `data` where the Data being parsed lies.
        """

        with data.make_child(
            relative=self._relative,
            addr_type=self._addr_type,
            revertible=self._optional,
        ) as new_data:
            if self._label:
                out_context = Context()
            else:
                out_context = context.new_child()

            for element in self._elements:
                element._space_and_parse(  # pylint: disable=protected-access
                    new_data, out_context
                )

        if self._label:
            self._store(context, dict(out_context))
        else:
            out_context.update_ext()


def Optional(*args, **kwargs) -> Block:  # pylint: disable=invalid-name
    """Shorthand for generating an optional `Block`.

    Takes the same arguments as a `Block`.

    Returns:
        An optional `Block`
    """
    return Block(*args, optional=True, **kwargs)


def _spacer(
    data: ds.DataSource,
    context: Context,
    stop_addr: int,
):
    """Reads a spacer into a context dictionary

    Args:
        data: Data being parsed
        context: Where results are stored
        stop_addr: The address of the first bit or byte in `data_source` to be excluded

    """
    start_addr = data.address
    length = stop_addr - start_addr

    if length == 0:
        return
    if length > 1:
        spacer_label = "spacer_" + hex(start_addr) + "-" + hex(stop_addr - 1)
    else:
        spacer_label = "spacer_" + hex(start_addr)

    context[spacer_label] = data.read(length)


class Context(collections.ChainMap):
    """Contains the results from parsing in a nested manner, allowing reverting failed
    optional data reads"""

    def __setitem__(self, key: str, value: Any) -> None:
        """Sets the underlying ChainMap value but updates duplicate keys

        Args:
            key: _description_
            value: _description_
        """
        new_key = key
        i = 1
        while new_key in self:
            new_key = key + " " + str(i)
            i = i + 1
        super().__setitem__(new_key, value)

    def update_ext(self) -> None:
        """Loads all of the current Context values into the parent Context"""
        if len(self.maps) == 1:
            raise RuntimeError
        self.maps[1].update(self.maps[0])
        self.maps[0].clear()
