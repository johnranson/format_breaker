# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access

from io import BytesIO
import pytest
from formatbreaker.datasource import DataManager, DATA_BUFFER_SIZE
from formatbreaker.bitwisebytes import BitwiseBytes
from formatbreaker.exceptions import FBError, FBNoDataError

src_data = bytes(range(256)) * 16


class TestDataSource:

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_basic_bit_reading(self, src):
        with DataManager(src) as data:

            b = data.read_bits(1025)
            c = data.read_bits(1025)
            d = data.read_bits()

        assert b == BitwiseBytes(src_data, 0, 1025)
        assert c == BitwiseBytes(src_data, 1025, 2050)
        assert d == BitwiseBytes(src_data, 2050)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_basic_byte_reading(self, src):
        with DataManager(src) as data:

            b = data.read_bytes(1025)
            c = data.read_bytes(1025)
            d = data.read_bytes()

        assert b == src_data[0:1025]
        assert c == src_data[1025:2050]
        assert d == src_data[2050:]

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bytes_at_eof_raises_exception(self, src):
        with DataManager(src) as data:

            _ = data.read_bytes(4096)

            with pytest.raises(FBNoDataError):
                _ = data.read_bytes(1)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bits_at_eof_raises_exception(self, src):
        with DataManager(src) as data:

            _ = data.read_bits(32768)

            with pytest.raises(FBNoDataError):
                _ = data.read_bits(1)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bytes_past_eof_raises_exception(self, src):
        with DataManager(src) as data:

            with pytest.raises(FBNoDataError):
                _ = data.read_bytes(4097)

    @pytest.mark.parametrize("src", [src_data, BytesIO(src_data)])
    def test_read_bits_past_eof_raises_exception(self, src):
        with DataManager(src) as data:

            with pytest.raises(FBNoDataError):
                _ = data.read_bits(32769)

    def test_buffers_added_and_trimmed_reading_to_buffer_end(self):
        with DataManager(BytesIO(src_data)) as data:
            assert data._buffer.lower_bound == 0
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE
            _ = data.read_bits(DATA_BUFFER_SIZE)
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE
            _ = data.read_bits(1)
            assert data._buffer.lower_bound == DATA_BUFFER_SIZE
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE * 2
            _ = data.read_bits(DATA_BUFFER_SIZE + 7)
            assert data._buffer.lower_bound == DATA_BUFFER_SIZE * 2
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE * 3

    def test_buffers_added_and_trimmed_reading_large_length(self):
        with DataManager(BytesIO(src_data)) as data:
            assert data._buffer.lower_bound == 0
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE
            _ = data.read_bits(DATA_BUFFER_SIZE * 3)
            assert data._buffer.lower_bound == DATA_BUFFER_SIZE
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE * 3

    def test_buffers_added_and_trimmed_reading_to_buffer_end_with_revertible(self):
        with DataManager(BytesIO(src_data)) as data:

            with data.make_child(revertible=True) as child:
                assert child._buffer.lower_bound == 0
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE
                _ = child.read_bits(DATA_BUFFER_SIZE)
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE
                _ = child.read_bits(1)
                assert child._buffer.lower_bound == 0
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE * 2
                _ = child.read_bits(DATA_BUFFER_SIZE + 7)
                assert child._buffer.lower_bound == 0
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE * 3
                assert child._cursor == DATA_BUFFER_SIZE * 2 + 8
                raise FBError

            assert data._buffer.lower_bound == 0
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE * 3
            assert data._cursor == 0

            with data.make_child(revertible=True) as child:
                _ = child.read_bits(DATA_BUFFER_SIZE)
                _ = child.read_bits(1)
                _ = child.read_bits(DATA_BUFFER_SIZE + 7)
                assert child._buffer.lower_bound == 0
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE * 3
                assert child._cursor == DATA_BUFFER_SIZE * 2 + 8

            assert data._buffer.lower_bound == DATA_BUFFER_SIZE * 2
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE * 3
            assert data._cursor == DATA_BUFFER_SIZE * 2 + 8

    def test_buffers_added_and_trimmed_reading_large_length_with_revertible(self):
        with DataManager(BytesIO(src_data)) as data:

            with data.make_child(revertible=True) as child:
                assert child._buffer.lower_bound == 0
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE
                _ = child.read_bits(DATA_BUFFER_SIZE * 3)
                assert child._buffer.lower_bound == 0
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE * 3
                assert child._cursor == DATA_BUFFER_SIZE * 3
                raise FBError

            assert data._buffer.lower_bound == 0
            assert data._buffer.upper_bound == DATA_BUFFER_SIZE * 3
            assert data._cursor == 0

            with data.make_child(revertible=True) as child:
                _ = child.read_bits(DATA_BUFFER_SIZE * 3)
                assert child._buffer.lower_bound == 0
                assert child._buffer.upper_bound == DATA_BUFFER_SIZE * 3
                assert child._cursor == DATA_BUFFER_SIZE * 3

        assert data._buffer.lower_bound == DATA_BUFFER_SIZE
        assert data._buffer.upper_bound == DATA_BUFFER_SIZE * 3
        assert data._cursor == DATA_BUFFER_SIZE * 3

    def test_buffers_with_nested_revertible(self):
        with DataManager(BytesIO(src_data)) as data:
            with data.make_child(revertible=True) as child1:
                _ = child1.read_bits(DATA_BUFFER_SIZE * 3)
                assert child1._cursor == DATA_BUFFER_SIZE * 3
                with child1.make_child(revertible=True) as child2:
                    # Read past the end
                    _ = child2.read_bits(DATA_BUFFER_SIZE * 3)
                assert child1._cursor == DATA_BUFFER_SIZE * 3
                with child1.make_child(revertible=True) as child3:
                    _ = child3.read_bits(DATA_BUFFER_SIZE)
                assert child1._cursor == DATA_BUFFER_SIZE * 4
                # Read past the end
                _ = child1.read_bits(DATA_BUFFER_SIZE)
            assert data._cursor == 0

    def test_incorrect_child_management_raises_error(self):
        with DataManager(BytesIO(src_data)) as data:
            with data.make_child() as child1:
                child1.read(1)
                with pytest.raises(RuntimeError):
                    with data.make_child() as _:
                        pass
                with pytest.raises(RuntimeError):
                    _ = data.read(1)
                with pytest.raises(RuntimeError):
                    _ = data.read_bits(1)
                with pytest.raises(RuntimeError):
                    _ = data.read_bytes(1)
                with pytest.raises(RuntimeError):
                    _ = data.address
                with pytest.raises(RuntimeError):
                    data._trim()

        data = DataManager(BytesIO(src_data))
        with pytest.raises(RuntimeError):
            with data.make_child() as _:
                pass
        with pytest.raises(RuntimeError):
            _ = data.read(1)
        with pytest.raises(RuntimeError):
            _ = data.read_bits(1)
        with pytest.raises(RuntimeError):
            _ = data.read_bytes(1)
        with pytest.raises(RuntimeError):
            _ = data.address
        with pytest.raises(RuntimeError):
            data._trim()
