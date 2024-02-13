import pytest
from formatbreaker.core import Parser, FBError, Block
from formatbreaker.util import BitwiseBytes, Context


class TestParser:

    @pytest.fixture
    def default_dt(self):
        return Parser()

    @pytest.fixture
    def context(self):
        return Context()

    def test_constructor_defaults_to_no_label_and_address(self, default_dt, context):

        assert default_dt._label is None
        assert default_dt._address is None

        with pytest.raises(RuntimeError):
            default_dt._store(context, "123")

    def test_copy_works_after_default_constructor(self, default_dt):

        copy_test_type = default_dt()

        assert copy_test_type is not default_dt
        assert copy_test_type._label is None
        assert copy_test_type._address is None

    def test_bad_constructor_types_raise_exceptions(self):
        with pytest.raises(TypeError):
            Parser("label", "address")

        with pytest.raises(TypeError):
            Parser(3, 3)

    def test_negative_address_raises_exception(self):
        with pytest.raises(IndexError):
            Parser("label", -1)

    @pytest.fixture
    def labeled_dt(self):
        return Parser("label", 3)

    def test_constructor_with_arguments_saves_label_and_address(self, labeled_dt):
        assert labeled_dt._label == "label"
        assert labeled_dt._address == 3
        assert labeled_dt._decode("123") == "123"

    def test_copy_works_after_constructor_with_label_and_address(self, labeled_dt):
        copy_test_type = labeled_dt()

        assert copy_test_type is not labeled_dt
        assert copy_test_type._label == "label"
        assert copy_test_type._address == 3

    def test_repeated_storing_and_updating_produces_expected_dictionary(
        self, labeled_dt, context
    ):
        labeled_dt._store(context, "123")
        labeled_dt._store(context, "456")
        labeled_dt._update(context, {"test": "123"})
        labeled_dt._update(context, {"test": "456"})
        labeled_dt._update(context, {})

        assert context == {
            "label": "123",
            "label 1": "456",
            "test": "123",
            "test 1": "456",
        }

    def test_default_parser_performs_no_op(self, labeled_dt, context):
        result = labeled_dt._parse(b"123567", context, 3)

        assert result == 3
        assert context == {}

    def test_parsing_wrong_address_raises_error(self, labeled_dt, context):
        with pytest.raises(IndexError):
            labeled_dt._parse(b"123567", context, 4)

    def test_space_and_parse_raises_error_past_required_address(
        self, labeled_dt, context
    ):
        with pytest.raises(FBError):
            result = labeled_dt._space_and_parse(b"123456", context, 5)

    def test_space_and_parse_does_not_create_spacer_if_at_address(
        self, labeled_dt, context
    ):
        result = labeled_dt._space_and_parse(b"123456", context, 3)
        assert result == 3
        assert not bool(context)

    def test_space_and_parse_creates_spacer_if_before_required_address(
        self, labeled_dt, context
    ):
        result = labeled_dt._space_and_parse(b"123456", context, 1)

        assert result == 3
        assert context["spacer_0x1-0x2"] == b"23"


class TestBlock:
    class MockType(Parser):
        _backup_label = "mock"

        def __init__(self, length=None, value=None, **kwargs) -> None:
            self.value = value
            self.length = length
            super().__init__(**kwargs)

        def _parse(self, data, context, addr):
            end_addr = addr + self.length
            self._store(context, self.value, addr=addr)
            return end_addr

    @pytest.fixture
    def empty_block(self):
        return Block()

    def test_empty_block_returns_empty_dict_on_parsing(self, empty_block):
        assert empty_block.parse(b"abc") == {}

    def test_block_constructor_fails_with_bad_data(self, empty_block):
        with pytest.raises(TypeError):
            Block("test")
        with pytest.raises(TypeError):
            Block(relative="true")
        with pytest.raises(TypeError):
            Block(bitwise="true")

    @pytest.fixture
    def sequential_block(self):
        return Block(
            TestBlock.MockType(3, "foo"),
            TestBlock.MockType(5, "bar"),
            TestBlock.MockType(1, "baz"),
        )

    def test_block_returns_parsing_results_from_all_elements(self, sequential_block):
        result = sequential_block.parse(b"12354234562")
        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
        }

    def test_bytewise_block_raises_error_with_bits(self, sequential_block):
        with pytest.raises(ValueError):
            sequential_block.parse(BitwiseBytes(b"12354234562"))

    def test_block_returns_error_if_parsing_elements_parse_past_end_of_input(
        self, sequential_block
    ):

        with pytest.raises(RuntimeError):
            sequential_block.parse(b"12")

    def test_non_relative_bitwise_block_parsing_bytewise_data_raises_error(self):
        with pytest.raises(RuntimeError):
            Block(relative=False, bitwise=True).parse(b"123")

    def test_non_relative_bitwise_block_parsing_bitwise_data_succeeds(self):
        Block(relative=False, bitwise=True).parse(BitwiseBytes(b"123"))

    @pytest.fixture
    def bitwise_sequential_block(self):
        return Block(
            TestBlock.MockType(3, "foo"),
            TestBlock.MockType(4, "bar"),
            TestBlock.MockType(1, "baz"),
            bitwise=True,
        )

    def test_bitwise_block_works_on_bytewise_data(self, bitwise_sequential_block):
        result = bitwise_sequential_block.parse(b"12354234562")
        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x7": "baz",
        }

    def test_bitwise_block_works_on_bitwise_data(self, bitwise_sequential_block):
        result = bitwise_sequential_block.parse(BitwiseBytes(b"12354234562"))
        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x7": "baz",
        }

    @pytest.fixture
    def bitwise_sequential_block_length_9(self):
        return Block(
            TestBlock.MockType(3, "foo"),
            TestBlock.MockType(5, "bar"),
            TestBlock.MockType(1, "baz"),
            bitwise=True,
        )

    def test_bitwise_block_parsing_bytewise_data_ending_off_byte_boundary_raises_error(
        self, bitwise_sequential_block_length_9
    ):
        with pytest.raises(RuntimeError):
            bitwise_sequential_block_length_9.parse(b"12354234562")

    def test_bitwise_block_parsing_bitwise_data_ending_off_byte_boundary_succeeds(
        self, bitwise_sequential_block_length_9
    ):
        result = bitwise_sequential_block_length_9.parse(BitwiseBytes(b"12354234562"))
        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
        }

    @pytest.fixture
    def addressed_block(self):
        return Block(
            TestBlock.MockType(3, "foo"),
            TestBlock.MockType(5, "bar"),
            TestBlock.MockType(1, "baz"),
            TestBlock.MockType(2, "qux", address=10),
        )

    def test_block_gets_spacer_with_addressed_elements(self, addressed_block):

        result = addressed_block.parse(b"\0" * 100)

        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
            "spacer_0x9": b"\x00",
            "mock_0xa": "qux",
        }

    def test_nested_blocks_produce_expected_results(self, addressed_block):
        cnk = Block(
            addressed_block,
            addressed_block("label"),
            addressed_block("label", 40),
            addressed_block(address=60),
        )

        result = cnk.parse(bytes(range(256)))

        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
            "spacer_0x9": b"\t",
            "mock_0xa": "qux",
            "label": {
                "mock_0x0": "foo",
                "mock_0x3": "bar",
                "mock_0x8": "baz",
                "spacer_0x9": b"\x15",
                "mock_0xa": "qux",
            },
            "spacer_0x18-0x27": b"\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !\"#$%&'",
            "label 1": {
                "mock_0x0": "foo",
                "mock_0x3": "bar",
                "mock_0x8": "baz",
                "spacer_0x9": b"1",
                "mock_0xa": "qux",
            },
            "spacer_0x34-0x3b": b"456789:;",
            "mock_0x0 1": "foo",
            "mock_0x3 1": "bar",
            "mock_0x8 1": "baz",
            "spacer_0x9 1": b"E",
            "mock_0xa 1": "qux",
        }
