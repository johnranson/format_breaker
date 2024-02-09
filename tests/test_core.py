import pytest
from formatbreaker.core import Parser, FBError, Batch


@pytest.fixture
def context():
    return {}


class TestParser:

    @pytest.fixture
    def default_dt(self):
        return Parser()

    def test_constructor_defaults_to_no_label_and_address(self, default_dt):

        assert default_dt._label is None
        assert default_dt._address is None

        context = {}
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


class TestBatch:
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
    def empty_Batch(self):
        return Batch()

    def test_empty_Batch_returns_empty_dict_on_parsing(self, empty_Batch):
        assert empty_Batch.parse(b"abc") == {}

    @pytest.fixture
    def sequential_Batch(self):
        return Batch(
            TestBatch.MockType(3, "foo"),
            TestBatch.MockType(5, "bar"),
            TestBatch.MockType(1, "baz"),
        )

    def test_Batch_returns_parsing_results_from_all_elements(
        self, sequential_Batch
    ):
        result = sequential_Batch.parse(b"12354234562")
        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
        }

    def test_Batch_returns_error_if_parsing_elements_parse_past_end_of_input(
        self, sequential_Batch
    ):

        with pytest.raises(RuntimeError):
            sequential_Batch.parse(b"12")

    @pytest.fixture
    def addressed_Batch(self):
        return Batch(
            TestBatch.MockType(3, "foo"),
            TestBatch.MockType(5, "bar"),
            TestBatch.MockType(1, "baz"),
            TestBatch.MockType(2, "qux", address=10),
        )

    def test_Batch_gets_spacer_with_addressed_elements(self, addressed_Batch):

        result = addressed_Batch.parse(b"\0" * 100)

        assert result == {
            "mock_0x0": "foo",
            "mock_0x3": "bar",
            "mock_0x8": "baz",
            "spacer_0x9": b"\x00",
            "mock_0xa": "qux",
        }

    def test_nested_Batchs_produce_expected_results(self, addressed_Batch):
        cnk = Batch(
            addressed_Batch,
            addressed_Batch("label"),
            addressed_Batch("label", 40),
            addressed_Batch(address=60),
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
