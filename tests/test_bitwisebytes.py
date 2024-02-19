# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access

import pytest
from formatbreaker.bitwisebytes import BitwiseBytes

src_data = bytes(range(256)) * 16


class TestBitwiseBytes:
    @pytest.fixture
    def bytedata(self):
        return b"\xff\x0f\x00\xff"

    @pytest.fixture
    def data(self, bytedata):
        return BitwiseBytes(bytedata)

    def test_invalid_constructor_inputs_raise_error(self, bytedata):
        with pytest.raises(TypeError):
            BitwiseBytes(bytedata, 1, "")  # type: ignore
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, -1, 1)
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, 0, -1)
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, 33, 1)
        with pytest.raises(IndexError):
            BitwiseBytes(bytedata, 1, 33)
        with pytest.raises(TypeError):
            BitwiseBytes(bytedata, "", 1)  # type: ignore
        with pytest.raises(TypeError):
            BitwiseBytes("", 1, 1)  # type: ignore

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
            _ = data["asdf"]

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
        empty = BitwiseBytes(b"")
        with pytest.raises(RuntimeError):
            int(empty)

    def test_too_high_subscript_raises_error(self, data):
        with pytest.raises(IndexError):
            _ = data[32]

    def test_too_low_subscript_raises_error(self, data):
        with pytest.raises(IndexError):
            _ = data[-33]

    def test_steps_other_than_one_raise_errors(self, data):
        with pytest.raises(NotImplementedError):
            _ = data[1:10:2]
        with pytest.raises(NotImplementedError):
            _ = data[1:10:-1]

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
