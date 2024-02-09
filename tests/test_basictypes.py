import pytest
from formatbreaker.core import FBError, Batch
from formatbreaker.basictypes import *


class TestByte:
    def test_reads_single_byte(self):
        assert Byte("name", 0).parse(b"5") == {"name": b"5"}

    def test_reads_positional_bytes(self):
        assert Byte("name", 0).parse(b"506") == {"name": b"5"}
        assert Byte("name", 1).parse(b"506")["name"] == b"0"
        assert Byte("name", 2).parse(b"506")["name"] == b"6"

        assert Byte(address=0).parse(b"506") == {"Byte_0x0": b"5"}
        assert Byte(address=1).parse(b"506")["Byte_0x1"] == b"0"
        assert Byte(address=2).parse(b"506")["Byte_0x2"] == b"6"

    def test_addressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert Byte("name", 0).parse(b"")

    def test_unaddressed_fails_with_no_byte_avail(self):
        with pytest.raises(FBError):
            assert Byte("name").parse(b"")

    def test_byte_address_out_of_range_raises_error(self):
        with pytest.raises(FBError):
            assert Byte("name", 3).parse(b"505")
