# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access

from io import BytesIO
import pytest
import formatbreaker.util as fu

src_data = bytes(range(256)) * 16


class TestDataSource:

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_basic_bit_reading(self, src):
        with fu.DataSource(src) as data:

            b = data.read_bits(1025)
            c = data.read_bits(1025)
            d = data.read_bits()

        assert b == fu.BitwiseBytes(src_data, 0, 1025)
        assert c == fu.BitwiseBytes(src_data, 1025, 2050)
        assert d == fu.BitwiseBytes(src_data, 2050)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_basic_byte_reading(self, src):
        with fu.DataSource(src) as data:

            b = data.read_bytes(1025)
            c = data.read_bytes(1025)
            d = data.read_bytes()

        assert b == src_data[0:1025]
        assert c == src_data[1025:2050]
        assert d == src_data[2050:]

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bytes_at_eof_raises_exception(self, src):
        with fu.DataSource(src) as data:

            _ = data.read_bytes(4096)

            with pytest.raises(fu.FBNoDataError):
                _ = data.read_bytes(1)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bits_at_eof_raises_exception(self, src):
        with fu.DataSource(src) as data:

            _ = data.read_bits(32768)

            with pytest.raises(fu.FBNoDataError):
                _ = data.read_bits(1)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bytes_past_eof_raises_exception(self, src):
        with fu.DataSource(src) as data:

            with pytest.raises(fu.FBNoDataError):
                _ = data.read_bytes(4097)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bits_past_eof_raises_exception(self, src):
        with fu.DataSource(src) as data:

            with pytest.raises(fu.FBNoDataError):
                _ = data.read_bits(32769)

    def test_buffers_added_and_trimmed_reading_to_buffer_end(self):
        with fu.DataSource(BytesIO(src_data)) as data:
            assert data._DataSource__bounds[0] == 0
            assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE
            _ = data.read_bits(fu.DATA_BUFFER_SIZE)
            assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE
            _ = data.read_bits(1)
            assert data._DataSource__bounds[0] == fu.DATA_BUFFER_SIZE
            assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE * 2
            _ = data.read_bits(fu.DATA_BUFFER_SIZE + 7)
            assert data._DataSource__bounds[0] == fu.DATA_BUFFER_SIZE * 2
            assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE * 3

    def test_buffers_added_and_trimmed_reading_large_length(self):
        with fu.DataSource(BytesIO(src_data)) as data:
            assert data._DataSource__bounds[0] == 0
            assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE
            _ = data.read_bits(fu.DATA_BUFFER_SIZE * 3)
            assert data._DataSource__bounds[0] == fu.DATA_BUFFER_SIZE
            assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE * 3

    def test_buffers_added_and_trimmed_reading_to_buffer_end_with_revertible(self):
        with fu.DataSource(BytesIO(src_data)) as data:

            with data.make_child(revertible=True) as child:
                assert child._DataSource__bounds[0] == 0
                assert child._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE
                _ = child.read_bits(fu.DATA_BUFFER_SIZE)
                assert child._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE
                _ = child.read_bits(1)
                assert child._DataSource__bounds[0] == 0
                assert child._DataSource__bounds[2] == fu.DATA_BUFFER_SIZE * 2
                _ = child.read_bits(fu.DATA_BUFFER_SIZE + 7)
                assert child._DataSource__bounds[0] == 0
                assert child._DataSource__bounds[3] == fu.DATA_BUFFER_SIZE * 3
                assert child._DataSource__cursor == fu.DATA_BUFFER_SIZE * 2 + 8
                raise fu.FBError

            assert data._DataSource__bounds[0] == 0
            assert data._DataSource__bounds[3] == fu.DATA_BUFFER_SIZE * 3
            assert data._DataSource__cursor == 0

            with data.make_child(revertible=True) as child:
                _ = child.read_bits(fu.DATA_BUFFER_SIZE)
                _ = child.read_bits(1)
                _ = child.read_bits(fu.DATA_BUFFER_SIZE + 7)
                assert child._DataSource__bounds[0] == 0
                assert child._DataSource__bounds[3] == fu.DATA_BUFFER_SIZE * 3
                assert child._DataSource__cursor == fu.DATA_BUFFER_SIZE * 2 + 8

            assert data._DataSource__bounds[0] == fu.DATA_BUFFER_SIZE * 2
            assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE * 3
            assert data._DataSource__cursor == fu.DATA_BUFFER_SIZE * 2 + 8

    def test_buffers_added_and_trimmed_reading_large_length_with_revertible(self):
        with fu.DataSource(BytesIO(src_data)) as data:

            with data.make_child(revertible=True) as child:
                assert child._DataSource__bounds[0] == 0
                assert child._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE
                _ = child.read_bits(fu.DATA_BUFFER_SIZE * 3)
                assert child._DataSource__bounds[0] == 0
                assert child._DataSource__bounds[2] == fu.DATA_BUFFER_SIZE * 3
                assert child._DataSource__cursor == fu.DATA_BUFFER_SIZE * 3
                raise fu.FBError

            assert data._DataSource__bounds[0] == 0
            assert data._DataSource__bounds[2] == fu.DATA_BUFFER_SIZE * 3
            assert data._DataSource__cursor == 0

            with data.make_child(revertible=True) as child:
                _ = child.read_bits(fu.DATA_BUFFER_SIZE * 3)
                assert child._DataSource__bounds[0] == 0
                assert child._DataSource__bounds[2] == fu.DATA_BUFFER_SIZE * 3
                assert child._DataSource__cursor == fu.DATA_BUFFER_SIZE * 3

        assert data._DataSource__bounds[0] == fu.DATA_BUFFER_SIZE
        assert data._DataSource__bounds[1] == fu.DATA_BUFFER_SIZE * 3
        assert data._DataSource__cursor == fu.DATA_BUFFER_SIZE * 3

    def test_buffers_with_nested_revertible(self):
        with fu.DataSource(BytesIO(src_data)) as data:
            with data.make_child(revertible=True) as child1:
                _ = child1.read_bits(fu.DATA_BUFFER_SIZE * 3)
                assert child1._DataSource__cursor == fu.DATA_BUFFER_SIZE * 3
                with child1.make_child(revertible=True) as child2:
                    # Read past the end
                    _ = child2.read_bits(fu.DATA_BUFFER_SIZE * 3)
                assert child1._DataSource__cursor == fu.DATA_BUFFER_SIZE * 3
                with child1.make_child(revertible=True) as child3:
                    _ = child3.read_bits(fu.DATA_BUFFER_SIZE)
                assert child1._DataSource__cursor == fu.DATA_BUFFER_SIZE * 4
                # Read past the end
                _ = child1.read_bits(fu.DATA_BUFFER_SIZE)
            assert data._DataSource__cursor == 0


    def test_incorrect_child_management_raises_error(self):
        with fu.DataSource(BytesIO(src_data)) as data:
            pass
        

@pytest.fixture
def spacer_stream_data():
    dat = bytes(range(128))
    return fu.DataSource(BytesIO(dat))


@pytest.fixture
def spacer_bytes_data():
    dat = bytes(range(256)) * 16
    return fu.DataSource(dat)


spacer_data = bytes(range(128))


class TestSpacer:

    @pytest.fixture
    def context(self):
        return fu.Context()

    def test_spacer_generates_expected_dictionary_and_return_value(self, context):
        with fu.DataSource(spacer_data) as data:
            data.read(1)
            fu.spacer(data, context, 6)
            assert context["spacer_0x1-0x5"] == bytes(spacer_data[1:6])

    def test_duplicate_spacer_generates_expected_dictionary_and_return_value(
        self, context
    ):
        with fu.DataSource(spacer_data) as data:
            context["spacer_0x1-0x5"] = bytes(spacer_data[1:6])
            data.read(1)
            fu.spacer(data, context, 6)
            assert context["spacer_0x1-0x5 1"] == bytes(spacer_data[1:6])

    def test_spacer_works_with_entire_input(self, context):
        with fu.DataSource(spacer_data) as data:
            fu.spacer(data, context, 128)
            assert context["spacer_0x0-0x7f"] == bytes(spacer_data)

    def test_length_one_beyond_input_size_raises_error(self, context):
        with fu.DataSource(spacer_data) as data:
            with pytest.raises(fu.FBNoDataError):
                fu.spacer(data, context, 129)

    def test_negative_address_raises_error(self, context):
        with fu.DataSource(spacer_data) as data:
            with pytest.raises(IndexError):
                fu.spacer(data, context, -1)

    def test_zero_length_spacer_is_no_op(self, context):
        with fu.DataSource(spacer_data) as data:
            fu.spacer(data, context, 0)
            assert context == {}


class TestBitwiseBytes:
    @pytest.fixture
    def bytedata(self):
        return b"\xff\x0f\x00\xff"

    @pytest.fixture
    def data(self, bytedata):
        return fu.BitwiseBytes(bytedata)

    def test_invalid_constructor_inputs_raise_error(self, bytedata):
        with pytest.raises(TypeError):
            fu.BitwiseBytes(bytedata, 1, "")  # type: ignore
        with pytest.raises(IndexError):
            fu.BitwiseBytes(bytedata, -1, 1)
        with pytest.raises(IndexError):
            fu.BitwiseBytes(bytedata, 0, -1)
        with pytest.raises(IndexError):
            fu.BitwiseBytes(bytedata, 33, 1)
        with pytest.raises(IndexError):
            fu.BitwiseBytes(bytedata, 1, 33)
        with pytest.raises(TypeError):
            fu.BitwiseBytes(bytedata, "", 1)  # type: ignore
        with pytest.raises(TypeError):
            fu.BitwiseBytes("", 1, 1)  # type: ignore

    def test_constructor_stop_bit_logic_ok(self, bytedata):
        with pytest.raises(IndexError):
            fu.BitwiseBytes(bytedata, 32, 33)
        assert bytes(fu.BitwiseBytes(bytedata, 32, 32)) == b""

    def test_converting_back_to_bytes_is_invariant(self, data, bytedata):
        assert bytes(data) == bytedata

    def test_copy_constructor_is_invariant(self, data):
        copy = fu.BitwiseBytes(data)
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
        empty = fu.BitwiseBytes(b"")
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
        assert empty_slice == fu.BitwiseBytes(b"")
        assert len(empty_slice) == 0

    def test_empty_data_behaves_appropriately(self):
        empty_bb = fu.BitwiseBytes(b"")

        assert len(empty_bb) == 0
        assert bytes(empty_bb) == b""
        assert not empty_bb.to_bools()
