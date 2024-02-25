# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access

import pytest
import formatbreaker.basictypes as bt
from formatbreaker.decoders import UInt8
from formatbreaker.datasource import DataManager, AddrType
from formatbreaker.exceptions import FBError
from formatbreaker.core import Context, Section


class TestByte:

    def test_reads_single_byte(self):
        assert (bt.Byte @ 0 >> "name").parse(b"5") == {"name": b"5"}

    @pytest.mark.parametrize("bytedata,bytesize", [(b"506", 1)])
    def test_reads_positional_bytes(self, bytedata: bytes, bytesize: int):
        assert (bt.Byte @ 0 >> "name").parse(bytedata) == {
            "name": bytes(bytedata[0:bytesize])
        }
        assert (bt.Byte @ bytesize >> "name").parse(bytedata)["name"] == bytes(
            bytedata[bytesize : 2 * bytesize]
        )
        assert (bt.Byte @ (2 * bytesize) >> "name").parse(bytedata)["name"] == bytes(
            bytedata[2 * bytesize : 3 * bytesize]
        )

        assert (bt.Byte @ 0).parse(bytedata) == {
            "Byte_0x0": bytes(bytedata[0:bytesize])
        }
        assert (bt.Byte @ bytesize).parse(bytedata)["Byte_" + hex(bytesize)] == bytes(
            bytedata[bytesize : 2 * bytesize]
        )
        assert (bt.Byte @ (2 * bytesize)).parse(bytedata)[
            "Byte_" + hex(bytesize * 2)
        ] == bytes(bytedata[2 * bytesize : 3 * bytesize])

    def test_addressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert (bt.Byte @ 0 >> "name").parse(b"")

    def test_unaddressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert (bt.Byte >> "name").parse(b"")

    def test_byte_address_out_of_range_raises_error(self):
        with pytest.raises(FBError):
            assert (bt.Byte @ 3 >> "name").parse(b"505")


class TestBytes:

    def test_reads_single_byte(self):
        assert bt.Bytes(1).parse(b"5") == {"Bytes_0x0": b"5"}

    def test_reads_all_byte(self):
        assert bt.Bytes(3).parse(b"506") == {"Bytes_0x0": b"506"}

    def test_reads_past_end_raises_error(self):
        with pytest.raises(FBError):
            bt.Bytes(4).parse(b"506")

    @pytest.mark.parametrize("bytedata,bytesize", [(b"506", 1)])
    def test_reads_positional_bytes(self, bytedata: bytes, bytesize: int):
        assert (bt.Bytes(1) @ 0 >> "name").parse(bytedata) == {
            "name": bytes(bytedata[0:bytesize])
        }
        assert (bt.Bytes(2) @ bytesize >> "name").parse(bytedata)["name"] == bytes(
            bytedata[bytesize : 3 * bytesize]
        )
        assert (bt.Bytes(1) @ (2 * bytesize) >> "name").parse(bytedata)[
            "name"
        ] == bytes(bytedata[2 * bytesize : 3 * bytesize])

        assert (bt.Bytes(1) @ 0).parse(bytedata) == {
            "Bytes_0x0": bytes(bytedata[0:bytesize])
        }
        assert (bt.Bytes(2) @ bytesize).parse(bytedata)[
            "Bytes_" + hex(bytesize)
        ] == bytes(bytedata[bytesize : 3 * bytesize])
        assert (bt.Bytes(1) @ (2 * bytesize)).parse(bytedata)[
            "Bytes_" + hex(bytesize * 2)
        ] == bytes(bytedata[2 * bytesize : 3 * bytesize])

    def test_addressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert (bt.Bytes(1) @ 0 >> "name").parse(b"")

    def test_unaddressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert (bt.Bytes(1) >> "name").parse(b"")

    def test_byte_address_out_of_range_raises_error(self):
        with pytest.raises(FBError):
            assert (bt.Bytes(1) @ 3 >> "name").parse(b"505")


class TestVarBytes:

    def test_missing_length_field_raises_error(self):
        with pytest.raises(KeyError):
            bt.VarBytes(source="length").parse(b"abcde")

    @pytest.fixture
    def test_section(self):
        return Section(UInt8 >> "length", bt.VarBytes(source="length"))

    def test_reads_single_byte(self, test_section: Section):
        assert test_section.parse(b"\x015")["VarBytes_0x1"] == b"5"

    def test_reads_all_byte(self, test_section: Section):
        assert test_section.parse(b"\xFF" + bytes(range(255)))["VarBytes_0x1"] == bytes(
            range(255)
        )

    def test_reads_past_end_raises_error(self, test_section: Section):
        with pytest.raises(FBError):
            test_section.parse(b"\x01")

    def test_invalid_length_key_raises_error(self):
        with pytest.raises(TypeError):
            bt.VarBytes(source=5)  # type: ignore
        with pytest.raises(TypeError):
            bt.VarBytes(source=None)  # type: ignore

    @pytest.fixture
    def test_section_address(self):
        return Section(UInt8 >> "length", bt.VarBytes(source="length") @ 5 >> "results")

    def test_reads_positional_bytes(self, test_section_address: Section):
        assert test_section_address.parse(b"\x0100005")["results"] == b"5"

    @pytest.fixture
    def test_section_bitwise(self):
        return Section(
            UInt8 >> "length",
            bt.VarBytes(source="length") @ 12 >> "results",
            bt.PadToAddress(24),
            addr_type=AddrType.BIT,
        )


def test_pad_to_address_bytewise():
    with DataManager(b"123456") as data:
        data.read_bytes(1)
        context = Context()
        bt.PadToAddress(5).goto_addr_and_read(data, context)
    assert dict(context) == {"spacer_0x1-0x4": b"2345"}


def test_pad_to_address_bitwise():
    with DataManager(b"\xF0") as data:
        context = Context()
        with data.make_child(addr_type=AddrType.BIT) as new_data:
            new_data.read(1)
            bt.PadToAddress(5).goto_addr_and_read(new_data, context)
            bt.PadToAddress(8).goto_addr_and_read(
                new_data, context
            )  # pylint: disable=protected-access

    assert dict(context) == {"spacer_0x1-0x4": b"\x0e", "spacer_0x5-0x7": b"\x00"}


def test_remnant_bytewise():
    with DataManager(b"123456") as data:
        data.read_bytes(1)
        context = Context()
        assert (bt.Remnant @ 1 >> "name").read(data, context) == b"23456"


def test_remant_bitwise():
    with DataManager(b"\xF0") as data:
        context = Context()
        with data.make_child(addr_type=AddrType.BIT) as new_data:
            new_data.read(1)
            assert (bt.Remnant @ 1 >> "name").read(new_data, context) == b"\x70"


class TestBit:

    def test_reads_single_bit(self):
        assert (bt.Bit @ 0 >> "name").parse(b"\xFF") == {"name": True}
        assert (bt.Bit @ 0 >> "name").parse(b"\x7F") == {"name": False}

    def test_reads_bits(self):
        bk = Section(bt.Bit[8] >> "Bit 0", addr_type=AddrType.BIT)
        result = bk.parse(b"\x55")
        assert result == {
            "Bit 0": [
                False,
                True,
                False,
                True,
                False,
                True,
                False,
                True,
            ]
        }

        result = bk.parse(b"\xAA")
        assert result == {
            "Bit 0": [
                True,
                False,
                True,
                False,
                True,
                False,
                True,
                False,
            ]
        }


class TestBitWord:
    @pytest.mark.parametrize(
        "length,offset,result", [(8, 0, 0xFF), (8, 1, 0xFE), (7, 1, 0x7F), (8, 8, 0x00)]
    )
    def test_reads_various_lengths_and_offsets(
        self, length: int, offset: int, result: int
    ):
        if offset == 0:
            bk = Section(
                bt.BitWord(length) >> "value",
                addr_type=AddrType.BIT,
            )
        else:
            bk = Section(
                bt.BitWord(offset) >> "ignore",
                bt.BitWord(length) >> "value",
                addr_type=AddrType.BIT,
            )
        assert int(bk.parse(b"\xff\0")["value"]) == result
