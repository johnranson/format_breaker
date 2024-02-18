# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import pytest
from formatbreaker.core import Block
import formatbreaker.basictypes as bt
from formatbreaker.decoders import UInt8
from formatbreaker.util import AddrType, FBError, DataSource, Context


class TestByte:

    def test_reads_single_byte(self):
        assert bt.Byte("name", 0).parse(b"5") == {"name": b"5"}

    @pytest.mark.parametrize("bytedata,bytesize", [(b"506", 1)])
    def test_reads_positional_bytes(self, bytedata, bytesize):
        assert bt.Byte("name", 0).parse(bytedata) == {
            "name": bytes(bytedata[0:bytesize])
        }
        assert bt.Byte("name", bytesize).parse(bytedata)["name"] == bytes(
            bytedata[bytesize : 2 * bytesize]
        )
        assert bt.Byte("name", 2 * bytesize).parse(bytedata)["name"] == bytes(
            bytedata[2 * bytesize : 3 * bytesize]
        )

        assert bt.Byte(address=0).parse(bytedata) == {
            "Byte_0x0": bytes(bytedata[0:bytesize])
        }
        assert bt.Byte(address=bytesize).parse(bytedata)[
            "Byte_" + hex(bytesize)
        ] == bytes(bytedata[bytesize : 2 * bytesize])
        assert bt.Byte(address=2 * bytesize).parse(bytedata)[
            "Byte_" + hex(bytesize * 2)
        ] == bytes(bytedata[2 * bytesize : 3 * bytesize])

    def test_addressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert bt.Byte("name", 0).parse(b"")

    def test_unaddressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert bt.Byte("name").parse(b"")

    def test_byte_address_out_of_range_raises_error(self):
        with pytest.raises(FBError):
            assert bt.Byte("name", 3).parse(b"505")


class TestBytes:

    def test_reads_single_byte(self):
        assert bt.Bytes(1).parse(b"5") == {"Bytes_0x0": b"5"}

    def test_reads_all_byte(self):
        assert bt.Bytes(3).parse(b"506") == {"Bytes_0x0": b"506"}

    def test_reads_past_end_raises_error(self):
        with pytest.raises(FBError):
            bt.Bytes(4).parse(b"506")

    @pytest.mark.parametrize("bytedata,bytesize", [(b"506", 1)])
    def test_reads_positional_bytes(self, bytedata, bytesize):
        assert bt.Bytes(1, "name", 0).parse(bytedata) == {
            "name": bytes(bytedata[0:bytesize])
        }
        assert bt.Bytes(2, "name", bytesize).parse(bytedata)["name"] == bytes(
            bytedata[bytesize : 3 * bytesize]
        )
        assert bt.Bytes(1, "name", 2 * bytesize).parse(bytedata)["name"] == bytes(
            bytedata[2 * bytesize : 3 * bytesize]
        )

        assert bt.Bytes(1, address=0).parse(bytedata) == {
            "Bytes_0x0": bytes(bytedata[0:bytesize])
        }
        assert bt.Bytes(2, address=bytesize).parse(bytedata)[
            "Bytes_" + hex(bytesize)
        ] == bytes(bytedata[bytesize : 3 * bytesize])
        assert bt.Bytes(1, address=2 * bytesize).parse(bytedata)[
            "Bytes_" + hex(bytesize * 2)
        ] == bytes(bytedata[2 * bytesize : 3 * bytesize])

    def test_addressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert bt.Bytes(1, "name", 0).parse(b"")

    def test_unaddressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert bt.Bytes(1, "name").parse(b"")

    def test_byte_address_out_of_range_raises_error(self):
        with pytest.raises(FBError):
            assert bt.Bytes(1, "name", 3).parse(b"505")


class TestVarBytes:

    def test_missing_length_field_raises_error(self):
        with pytest.raises(KeyError):
            bt.VarBytes(source="length").parse(b"abcde")

    @pytest.fixture
    def test_block(self):
        return Block(UInt8("length"), bt.VarBytes(source="length"))

    def test_reads_single_byte(self, test_block):
        assert test_block.parse(b"\x015")["VarBytes_0x1"] == b"5"

    def test_reads_all_byte(self, test_block):
        assert test_block.parse(b"\xFF" + bytes(range(255)))["VarBytes_0x1"] == bytes(
            range(255)
        )

    def test_reads_past_end_raises_error(self, test_block):
        with pytest.raises(FBError):
            test_block.parse(b"\x01")

    def test_invalid_length_key_raises_error(self):
        with pytest.raises(TypeError):
            bt.VarBytes(source=5)
        with pytest.raises(TypeError):
            bt.VarBytes(source=None)

    @pytest.fixture
    def test_block_address(self):
        return Block(UInt8("length"), bt.VarBytes("results", 5, source="length"))

    def test_reads_positional_bytes(self, test_block_address):
        assert test_block_address.parse(b"\x0100005")["results"] == b"5"

    @pytest.fixture
    def test_block_bitwise(self):
        return Block(
            UInt8("length"),
            bt.VarBytes("results", 12, source="length"),
            bt.PadToAddress(24),
            bitwise=True,
        )


def test_pad_to_address_bytewise():
    data = DataSource(source=b"123456")
    data.read_bytes(1)
    context = Context()
    bt.PadToAddress(5)._space_and_parse(data, context) #pylint: disable=protected-access
    assert dict(context) == {"spacer_0x1-0x4": b"2345"}


def test_pad_to_address_not_callable():
    with pytest.raises(NotImplementedError):
        bt.PadToAddress(5)()


def test_pad_to_address_bitwise():
    data = DataSource(source=b"\xF0")
    context = Context()
    with data.make_child(addr_type=AddrType.BIT) as new_data:
        new_data.read(1)
        bt.PadToAddress(5)._space_and_parse(new_data, context) #pylint: disable=protected-access
        bt.PadToAddress(8)._space_and_parse(new_data, context) #pylint: disable=protected-access

    assert dict(context) == {"spacer_0x1-0x4": b"\x0e", "spacer_0x5-0x7": b"\x00"}


def test_remnant_bytewise():
    data = DataSource(source=b"123456")
    data.read_bytes(1)
    context = Context()
    bt.Remnant("name", 1)._parse(data, context) #pylint: disable=protected-access
    assert dict(context) == {"name": b"23456"}


# def test_remnant_bytewise():
#     data = DataSource(source=b"\xF0")
#     data.read_bytes(1)
#     context = Context()
#     Remnant("name", 1)._parse(data, context)
#     assert dict(context) == {"name": b"23456"}


def test_remant_bitwise():
    data = DataSource(source=b"\xF0")
    context = Context()
    with data.make_child(addr_type=AddrType.BIT) as new_data:
        new_data.read(1)
        bt.Remnant("name", 1)._parse(new_data, context) #pylint: disable=protected-access
    assert dict(context) == {"name": b"\x70"}
