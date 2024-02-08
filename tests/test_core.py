import pytest
from formatbreaker.core import DataType, FBError, Chunk


@pytest.fixture
def context():
    return {}


class TestDataType:

    @pytest.fixture
    def default_dt(self):
        return DataType()

    def test_constructor_defaults_to_no_name_and_address(self, default_dt):

        assert default_dt.name is None
        assert default_dt.address is None

        context = {}
        with pytest.raises(RuntimeError):
            default_dt._store(context, "123")

    def test_copy_works_after_default_constructor(self, default_dt):

        copy_test_type = default_dt()

        assert copy_test_type is not default_dt
        assert copy_test_type.name is None
        assert copy_test_type.address is None

    def test_bad_constructor_types_raise_exceptions(self):
        with pytest.raises(TypeError):
            DataType("name", "address")

        with pytest.raises(TypeError):
            DataType(3, 3)

    def test_negative_address_raises_exception(self):
        with pytest.raises(IndexError):
            DataType("name", -1)

    @pytest.fixture
    def named_dt(self):
        return DataType("name", 3)

    def test_constructor_with_arguments_saves_name_and_address(self, named_dt):
        assert named_dt.name == "name"
        assert named_dt.address == 3
        assert named_dt._decode("123") == "123"

    def test_copy_works_after_constructor_with_name_and_address(self, named_dt):
        copy_test_type = named_dt()

        assert copy_test_type is not named_dt
        assert copy_test_type.name == "name"
        assert copy_test_type.address == 3

    def test_repeated_storing_and_updating_produces_expected_dictionary(
        self, named_dt, context
    ):
        named_dt._store(context, "123")
        named_dt._store(context, "456")
        named_dt._update(context, {"test": "123"})
        named_dt._update(context, {"test": "456"})
        named_dt._update(context, {})

        assert context == {
            "name": "123",
            "name 1": "456",
            "test": "123",
            "test 1": "456",
        }

    def test_default_parser_performs_no_op(self, named_dt, context):
        result = named_dt._parse(b"123", context, 5)

        assert result == 5
        assert context == {}

    def test_space_and_parse_raises_error_past_required_address(
        self, named_dt, context
    ):
        with pytest.raises(FBError):
            result = named_dt._space_and_parse(b"123456", context, 5)

    def test_space_and_parse_does_not_create_spacer_if_at_address(
        self, named_dt, context
    ):
        result = named_dt._space_and_parse(b"123456", context, 3)
        assert result == 3
        assert not bool(context)

    def test_space_and_parse_creates_spacer_if_before_required_address(
        self, named_dt, context
    ):
        result = named_dt._space_and_parse(b"123456", context, 1)

        assert result == 3
        assert context["spacer_0x1-0x2"] == b"23"


class TestChunk:
    class MockType(DataType):
        backupname = "mock"

        def __init__(self, length=None, value=None, **kwargs) -> None:
            self.value = value
            self.length = length
            super().__init__(**kwargs)

        def _parse(self, data, context, addr):
            end_addr = addr + self.length
            self._store(context, self.value, addr=addr)
            return end_addr

    @pytest.fixture
    def empty_chunk(self):
        return Chunk()

    def test_empty_chunk_returns_empty_dict_on_parsing(self, empty_chunk):
        assert empty_chunk.parse(b"abc") == {}

    @pytest.fixture
    def sequential_chunk(self):
        return Chunk(
            TestChunk.MockType(3, "foo"),
            TestChunk.MockType(5, "bar"),
            TestChunk.MockType(1, "baz"),
        )

    def test_chunk_returns_parsing_results_from_all_elements(self, sequential_chunk):
        result = sequential_chunk.parse(b"12354234562")
        assert result == {"mock_0x0": "foo", "mock_0x3": "bar", "mock_0x8": "baz"}

    def test_chunk_returns_error_if_parsing_elements_parse_past_end_of_input(
        self, sequential_chunk
    ):

        with pytest.raises(RuntimeError):
            sequential_chunk.parse(b"12")

    @pytest.fixture
    def addressed_chunk(self):
        return Chunk(
            TestChunk.MockType(3, "foo"),
            TestChunk.MockType(5, "bar"),
            TestChunk.MockType(1, "baz"),
            TestChunk.MockType(2, "qux", address=10),
        )

    def test_chunk_gets_spacer_with_addressed_elements(self, addressed_chunk):

        result = addressed_chunk.parse(b"\0" * 100)

        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
            "spacer_0x9": b"\x00",
            "mock_0xa": "qux",
        }

    def test_nested_chunks_produce_expected_results(self, addressed_chunk):
        cnk = Chunk(
            addressed_chunk,
            addressed_chunk("name"),
            addressed_chunk("name", 40),
            addressed_chunk(address=60),
        )

        result = cnk.parse(bytes(range(256)))

        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
            "spacer_0x9": b"\t",
            "mock_0xa": "qux",
            "name": {
                "mock_0x0": "foo",
                "mock_0x3": "bar",
                "mock_0x8": "baz",
                "spacer_0x9": b"\x15",
                "mock_0xa": "qux",
            },
            "spacer_0x18-0x27": b"\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !\"#$%&'",
            "name 1": {
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
