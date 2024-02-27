"""This module contains the basic Parser, Block (Parser container), and Context (Parser
data storage) code"""

# pyright: reportUnnecessaryComparison=false
# pyright: reportUnnecessaryIsInstance=false

from __future__ import annotations
from typing import ClassVar, Any, override, Callable, final
from abc import ABC, abstractmethod
import copy
import io
import collections
from formatbreaker.util import validate_address_or_length
from formatbreaker.datasource import DataManager, AddrType


class Context(collections.ChainMap[str, Any]):
    """Contains the results from parsing in a nested manner, allowing reverting failed
    optional data reads"""

    def __setitem__(self, key: str, value: Any) -> None:
        """Sets the underlying ChainMap value but renames duplicate keys

        Args:
            key: A string dictionary key
            value: The value to store with the given `key`
        """
        parts = key.split(" ")
        if parts[-1].isnumeric():
            base = " ".join(parts[0:-1])
            i = int(parts[-1])
            new_key = base + " " + str(i)
        else:
            base = key
            i = 1
            new_key = key

        while new_key in self:
            new_key = base + " " + str(i)
            i = i + 1
        super().__setitem__(new_key, value)

    def update_ext(self) -> None:
        """Loads all of the current Context values into the parent Context"""
        if len(self.maps) == 1:
            raise RuntimeError
        self.maps[1].update(self.maps[0])
        self.maps[0].clear()


type Contexts = tuple[Context, ...]
# This is a list of all contexts created since parse() was called
# in order of newest to oldest. It only intended to include contexts
# that have no parent-child relationship. When a new child is created
# for the most recent context, it should just replace the parent if
# it is passed in a Contexts tuple.
# When a Block or Array is parsed, we have to create a new context
# in the elements store their results. The new context is not a child of
# a previous contexts, but the elements of the block or array may
# need to reference values in previous contexts. Thus, we pass around
# this tuple of all past contexts, allowing any parser to reference any
# data stored at any time during the parsing.


def get_from_contexts(contexts: Contexts, key: str | tuple):
    """Fetches a value from the past Contexts

    If a string key is provided, it returns the first value it can
    find for that key, searching contexts from newest to oldes

    If a tuple is provided, it should be an integer n followed by
    any number of string or integer keys. It will then recursively
    lookup the keys in order in the nth context, allowing reading
    a value from any dictionary or list stored therein.

    Args:
        contexts: A tuple of contexts
        key: A string key for a simple lookup, or a tuple containing an integer and any
        number of keys.

        get_from_contexts(con, (n, A, B, C, D, ...)) ==
        con[n][A][B][C][D]...
    Returns:
        The value retrieved from the `contexts`
    """
    if isinstance(key, str):
        for context in contexts:
            if key in context:
                return context[key]
        raise KeyError
    if isinstance(key, tuple):
        result = contexts
        for subkey in key:
            result = result[subkey]
        return result


def _spacer(
    data: DataManager,
    context: Context,
    stop_addr: int,
):
    """Reads a spacer into a context dictionary

    Args:
        data: The data being parsed
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


class ParseResult:
    """Returned by Parser.read() when there is no data to return"""


class Reverted(ParseResult):
    """Returned by an Optional.read() that fails"""


class Success(ParseResult):
    """Returned after a successful Parser.read() with no return data"""


class Parser(ABC):
    """This is the basic parser implementation that most parsers inherit from"""

    __slots__ = ("__label", "_backup_label", "__addr_type", "__address")
    __label: str | None
    _backup_label: str
    _default_backup_label: ClassVar[str] = "Data"
    __addr_type: AddrType
    _backup_addr_type: ClassVar[AddrType] = AddrType.BYTE
    __address: int | None

    @property
    def _label(self) -> str | None:
        return self.__label

    @_label.setter
    def _label(self, label: str) -> None:
        if label is not None and not isinstance(label, str):
            raise TypeError("Parser labels must be strings")
        self.__label = label

    @property
    def _addr_type(self) -> AddrType:
        return self.__addr_type

    @_addr_type.setter
    def _addr_type(self, addr_type: AddrType | str) -> None:
        if isinstance(addr_type, str):
            self.__addr_type = AddrType[addr_type]
        elif isinstance(addr_type, AddrType):
            self.__addr_type = addr_type
        else:
            raise TypeError("Address type must be ")

    @property
    def _address(self) -> int | None:
        return self.__address

    @_address.setter
    def _address(self, address: int) -> None:
        if address is not None:
            validate_address_or_length(address)
        self.__address = address

    def __init__(self) -> None:
        self.__address = None
        self.__label = None
        self._addr_type = AddrType.PARENT
        self._backup_label = self._default_backup_label

    @abstractmethod
    def read(self, data: DataManager, contexts: Contexts) -> Any:
        """Reads data from the current address

        Must be overridden by any subclass

        Args:
            data: The data currently being parsed
            contexts: Past stored parsing results

        Returns:
            The data read
        """

    @final
    def read_and_translate(
        self,
        data: DataManager,
        contexts: Contexts,
    ) -> Any:
        """Reads and translates data from the current address

        Args:
            data: The data currently being parsed
            contexts: Past stored parsing results

        Returns:
            Translated data read
        """
        result = self.read(data, contexts)
        if result is Reverted:
            return Reverted
        return self.translate(result)

    @final
    def goto_addr_and_read(
        self, data: DataManager, contexts: Contexts
    ) -> type[ParseResult]:
        """Reads to the target address, and then read, translate and store results

        Args:
            data: The data currently being parsed
            contexts: Past stored parsing results. Where new results are stored.

        Returns:
            An indicator of how the parsing went
        """
        if self._address is not None:
            _spacer(data, contexts[0], self._address)
        addr = data.address
        result = self.read_and_translate(data, contexts)
        if result is Reverted:
            return Reverted
        if isinstance(result, Context):
            result.update_ext()
        elif result is None:
            raise ValueError
        elif result is not Success:
            self._store(contexts[0], result, addr)
        return Success

    @final
    def parse(
        self,
        data: bytes | io.BufferedIOBase,
    ) -> dict[str, Any]:
        """Parse the provided data from the beginning

        Args:
            data: The data to be parsed

        Returns:
            A dictionary of the results.
        """

        context = Context()
        if self._addr_type == AddrType.PARENT:
            addr_type = self._backup_addr_type
        else:
            addr_type = self._addr_type
        with DataManager(src=data, addr_type=addr_type) as manager:
            self.goto_addr_and_read(manager, (context,))
            return dict(context)
        return {}

    @final
    def _store(
        self,
        context: Context,
        data: Any,
        addr: int | None = None,
    ) -> None:
        """Store the value with a unique key

        If `label` is not provided, the code will use `self._label`. If
        `self._label` is None, it will default to the class `_backup_label`
        attribute.

        Args:
            context: Where results are to be stored
            data: The data to be stored
            addr: The location the data came from, used for unlabeled fields
        """
        if self._label:
            label = self._label
        else:
            label = self._backup_label
            if addr is not None:
                label = label + "_" + hex(addr)
        context[label] = data

    def translate(self, data: Any) -> Any:
        """Converts parsed data to another format

        Defaults to passing through the data unchanged.
        This may be overridden as needed by subclasses.

        Args:
            data: Input data from reading

        Returns:
            Translated output data
        """
        return data

    @final
    def __getitem__(self, qty: int):
        """Makes bracket notation create an array of this Parser

        Args:
            qty: Number of repetitions in the array

        Returns:
            An Array of this Parser
        """
        return Array(self, qty)

    @final
    def __mul__(self, qty: int):
        """Makes the * operator repeat a Parser

        Args:
            qty: Number of repetitions

        Returns:
            An Repeat of this instance
        """
        return Repeat(self, qty)

    @final
    def __matmul__(self, addr: int):
        """Makes the @ operator assign an address

        Args:
            addr: The new address

        Returns:
            A copy of this instance with the address set
        """
        b = copy.copy(self)
        b._address = addr
        return b

    @final
    def __rshift__(self, label: str):
        """Makes the >> operator assign a label

        Args:
            label: The new label

        Returns:
            A copy of this instance with the label set
        """
        if not isinstance(label, str):
            raise TypeError
        b = copy.copy(self)
        b._label = label
        return b


class MultiElement(Parser):
    """A parser that contains other parsers."""

    __slots__ = ("_relative", "_elements")
    _relative: bool
    _elements: tuple[Parser, ...]

    def __init__(
        self,
        *elements: Parser,
        relative: bool = True,
        addr_type: AddrType | str = AddrType.PARENT,
    ) -> None:
        """
        Args:
            *elements: Parsers this instance should hold, in order.
            relative: If True, addresses for `self.elements` are relative to this
                instance.
            addr_type: The way addresses for `self.elements` should be interpreted
                ie. bitwise or bytewise
        """
        super().__init__()
        if not isinstance(relative, bool):
            raise TypeError
        if not all(isinstance(item, Parser) for item in elements):
            raise TypeError

        self._addr_type = addr_type
        self._elements = elements
        self._relative = relative


class Block(MultiElement):
    """A parser that contains other parsers. The parsers are executed in order and the
    results stored in a new context. The new context is stored as a dictionary in the
    existing context after parsing."""

    _default_backup_label: ClassVar[str] = "Block"

    @override
    def read(
        self,
        data: DataManager,
        contexts: Contexts,
    ) -> dict[str, Any] | type[ParseResult]:
        """Parse the data using each Parser sequentially.

        Args:
            data: The data currently being parsed
            contexts: Past stored parsing results

        Returns:
            A dictionary of the results to be stored as a dict
        """

        with data.make_child(
            relative=self._relative, addr_type=self._addr_type
        ) as new_data:
            out_context = Context()
            for element in self._elements:
                element.goto_addr_and_read(new_data, (out_context, *contexts))
            return dict(out_context)
        return Reverted


class Section(MultiElement):
    """A parser that contains other parsers. The parsers are executed in order and the
    results stored in a child context. The child context is updated into the parent
    context after parsing."""

    __slots__ = ("_optional",)
    _default_backup_label: ClassVar[str] = "Section"
    _optional: bool

    def __init__(
        self,
        *elements: Parser,
        relative: bool = True,
        addr_type: AddrType | str = AddrType.PARENT,
        optional: bool = False,
    ) -> None:
        """
        Args:
            *elements: Parsers this Block should hold, in order.
            relative: If True, addresses for `self.elements` are relative to this
                Block.
            addr_type: The way addresses for `self.elements` should be interpreted
                ie. bitwise or bytewise
            optional: If True, if any of the contained elements fail to parse, the Block
                acts as a no-op and reverts the state of the data to when it started.
                Optional blocks may be nested. Only the innermost optional block will
                no-op and revert for a given failure

        """
        super().__init__(*elements, relative=relative, addr_type=addr_type)
        self._optional = optional

    @override
    def read(
        self,
        data: DataManager,
        contexts: Contexts,
    ) -> Context | type[ParseResult]:
        """
        Args:
            *elements: Parsers this Section should hold, in order.
            relative: If True, addresses for `self.elements` are relative to this
                Section.
            addr_type: The way addresses for `self.elements` should be interpreted
                ie. bitwise or bytewise
            optional: If True, if any of the contained elements fail to parse, the
                Section acts as a no-op and reverts the state of the data to when it
                started. Optional sections may be nested. Only the innermost optional
                block will no-op and revert for a given failure

        """
        with data.make_child(
            relative=self._relative,
            addr_type=self._addr_type,
            revertible=self._optional,
        ) as new_data:
            out_context = contexts[0].new_child()
            for element in self._elements:
                element.goto_addr_and_read(new_data, (out_context, *contexts[1:]))

            print(out_context)
            return out_context
        return Reverted


def Optional(*args: Any, **kwargs: Any) -> Section:  # pylint: disable=invalid-name
    """Shorthand for generating an optional `Section`.

    Takes the same arguments as a `Section`.

    Returns:
        An optional `Section`
    """
    return Section(*args, optional=True, **kwargs)


class Modifier(Parser):
    """A Parser that contains an instance of another Parser and copies its behavior
    with modifications.
    """

    __slots__ = ["_parser"]
    _parser: Parser

    def __init__(self, parser: Parser, backup_label: str | None = None) -> None:
        super().__init__()
        self._parser = parser
        if backup_label:
            self._backup_label = backup_label
        else:
            self._backup_label = parser._backup_label
        self._addr_type = parser._addr_type
        if parser._label:
            self._label = parser._label
        if parser._address:
            self._address = parser._address

    def read(
        self,
        data: DataManager,
        contexts: Contexts,
    ) -> Any:
        """Parses data

        Args:
            data: Data being parsed
            context: Where results old results are stored
        """
        return self._parser.read_and_translate(data, contexts)


class Translator(Modifier):
    """A Modifier that runs an additional translation function on the output
    of another Parser
    """

    __slots__ = ["_translate_func"]

    def __init__(
        self,
        parser: Parser,
        translate_func: Callable[[Any], Any],
        backup_label: str | None = None,
    ) -> None:
        super().__init__(parser, backup_label)
        self._translate_func: Callable[[Any], Any] = staticmethod(translate_func)

    def translate(self, data: Any) -> Any:
        return self._translate_func(data)


class Repeat(Modifier):
    """A Modifier that acts as if the contained Parser were parsed multiple times."""

    __slots__ = ["_repeat_qty"]

    def __init__(self, parser: Parser, repeat_qty: int | str) -> None:
        super().__init__(parser)
        validate_address_or_length(repeat_qty, 1)
        self._repeat_qty = repeat_qty

    @override
    def read(
        self,
        data: DataManager,
        contexts: Contexts,
    ) -> Context:
        """Parse the data using each Parser sequentially.

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the same
                containing Block
            addr: The bit or byte address in `data` where the Data being parsed lies.
        """

        if isinstance(self._repeat_qty, str):
            reps = get_from_contexts(contexts, self._repeat_qty)
        if isinstance(self._repeat_qty, int):
            reps = self._repeat_qty
        else:
            raise ValueError

        results = contexts[0].new_child()

        for _ in range(reps):
            with data.make_child(
                relative=True,
                addr_type=AddrType.PARENT,
                revertible=False,
            ) as new_data:
                addr = new_data.address
                out_context = results.new_child()
                result = self._parser.read_and_translate(new_data, contexts)
                if result is Reverted:
                    continue
                elif isinstance(result, Context):
                    result.update_ext()
                elif result is not None:
                    self._store(out_context, result, addr)
                out_context.update_ext()
        return results


class Array(Modifier):
    """A Modifier that creates a list of results during parsing by reading the
    contained Parser several times.
    """

    __slots__ = ["_repeat_qty"]

    def __init__(self, parser: Parser, repeat_qty: int | str) -> None:
        super().__init__(parser)
        validate_address_or_length(repeat_qty)
        self._repeat_qty = repeat_qty

    @override
    def read(
        self,
        data: DataManager,
        contexts: Contexts,
    ) -> list[Any] | type[ParseResult]:
        """Parse the data using each Parser sequentially.

        Args:
            data: Data being parsed
            context: Where results are stored including prior results in the same
                containing Block
            addr: The bit or byte address in `data` where the Data being parsed lies.
        """

        if isinstance(self._repeat_qty, str):
            reps = get_from_contexts(contexts, self._repeat_qty)
        if isinstance(self._repeat_qty, int):
            reps = self._repeat_qty
        else:
            raise ValueError

        results: list[Any] = []
        for _ in range(reps):
            with data.make_child(
                relative=True,
                addr_type=AddrType.PARENT,
                revertible=False,
            ) as new_data:
                out_context = Context()
                result = self._parser.read_and_translate(
                    new_data, (out_context, *contexts[1:])
                )
                if result is Reverted:
                    results.append([])
                elif isinstance(result, Context):
                    results.append(dict(result))  # Well, I guess that's okay
                elif result is not None:
                    results.append(result)
        return results
