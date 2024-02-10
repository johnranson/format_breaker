import pytest
from formatbreaker.util import *


def test_uniquify_label():
    context = {}
    assert uniquify_label("label", context) == "label"
    context = {"label": 2}
    assert uniquify_label("label", context) == "label 1"
    context.update({"label 1": 2})
    assert uniquify_label("label", context) == "label 2"


@pytest.mark.parametrize(
    "data", [bytes(range(128)), BitwiseBytes(bytes(range(16)))]
)
class TestSpacer:

    @pytest.fixture
    def context(self):
        return {}

    def test_spacer_generates_expected_dictionary_and_return_value(
        self, data, context
    ):
        result = spacer(data, context, 1, 6)
        assert result == 6
        assert context["spacer_0x1-0x5"] == bytes(data[1:6])

    def test_duplicate_spacer_generates_expected_dictionary_and_return_value(
        self, data, context
    ):
        result = spacer(data, context, 1, 6)
        result = spacer(data, context, 1, 6)
        assert result == 6
        assert context["spacer_0x1-0x5 1"] == bytes(data[1:6])

    def test_spacer_works_with_entire_input(self, data, context):
        result = spacer(data, context, 0, 128)
        assert result == 128
        print(context)
        assert context["spacer_0x0-0x7f"] == bytes(data)

    def test_length_one_beyond_input_size_raises_error(self, data, context):
        with pytest.raises(IndexError):
            result = spacer(data, context, 0, 129)

    def test_negative_address_raises_error(self, data, context):
        with pytest.raises(IndexError):
            result = spacer(data, context, -1, 5)
        with pytest.raises(IndexError):
            result = spacer(data, context, 1, -1)

    def test_address_beyond_input_size_raises_error(self, data, context):
        with pytest.raises(IndexError):
            result = spacer(data, context, 1000, 1)

    def test_zero_length_spacer_is_no_op(self, data, context):
        result = spacer(data, context, 1, 1)
        assert result == 1
        assert context == {}
        


class TestBitwiseBytes:
    @pytest.fixture
    def bytedata(self):
        return b"\xff\x0f\x00\xff"

    @pytest.fixture
    def data(self, bytedata):
        return BitwiseBytes(bytedata)

    def test_invalid_constructor_inputs_raise_error(self, bytedata):
        with pytest.raises(TypeError):
            BitwiseBytes(bytedata, 1, "")
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, -1, 1)
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, 0, -1)
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, 33, 1)
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, 1, 33)
        with pytest.raises(TypeError):
            BitwiseBytes(bytedata, "", 1)
        with pytest.raises(TypeError):
            BitwiseBytes("", 1, 1)

    def test_constructor_stop_bit_logic_ok(self, bytedata):
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, 32, 33)
        assert bytes(BitwiseBytes(bytedata, 32, 32)) == b""

    def test_converting_back_to_bytes_is_invariant(self, data, bytedata):
        assert bytes(data) == bytedata

    def test_copy_constructor_is_invariant(self, data):
        copy = BitwiseBytes(data)
        assert copy == data
        assert copy is not data
        
    def test_wrong_index_type_raises_error(self, data):
        with pytest.raises(ValueError):
            data['asdf']

    def test_slices_with_identical_contents_equal(self, data):
        assert data[0:8] == data[24:32]

    def test_slices_with_different_contents_are_unequal(self, data):
        assert data[0:9] != data[23:32]

    def test_slices_with_different_lengths_are_not_equal(self, data):
        assert int(data[8:12]) == int(data[16:24])
        assert data[8:12] != data[16:24]

    def test_slicing_cropped_to_data_range(self, data):
        assert data[-50:200] == data

    def test_to_bool_conversion_works(self, data):
        assert data.to_bools() == [
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            False,
            False,
            False,
            False,
            True,
            True,
            True,
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
        ]

    def test_len_function_works(self, data):
        assert len(data) == 32

    def test_len_function_works_on_slice(self, data):
        assert len(data[1:9]) == 8

    def test_int_conversion_works(self, data):
        assert int(data) == 4279173375
        
    def test_int_conversion_on_empty_failse(self):
        empty = BitwiseBytes(b'')
        with pytest.raises(RuntimeError):
            int(empty)

    def test_too_high_subscript_raises_error(self, data):
        with pytest.raises(IndexError):
            data[32]

    def test_too_low_subscript_raises_error(self, data):
        with pytest.raises(IndexError):
            data[-33]

    def test_steps_other_than_one_raise_errors(self, data):
        with pytest.raises(NotImplementedError):
            data[1:10:2]
        with pytest.raises(NotImplementedError):
            data[1:10:-1]

    def test_negative_and_positive_subscripts_read_matching_bits(self, data):
        for i in range(32):
            assert data[-1 - i] == data[31 - i]

    def test_empty_slices_behave_appropriately(self, data):
        empty_slice = data[:0]

        assert bytes(empty_slice) == b""
        assert empty_slice == BitwiseBytes(b"")
        assert len(empty_slice) == 0

    def test_empty_data_behaves_appropriately(self):
        empty_bb = BitwiseBytes(b"")

        assert len(empty_bb) == 0
        assert bytes(empty_bb) == b""
        assert not empty_bb.to_bools()
