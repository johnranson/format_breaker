# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access

import struct
import uuid
import pytest
import formatbreaker.decoders as fd
from formatbreaker.exceptions import FBError


def test_byte_flag():
    par = fd.ByteFlag()
    assert not par.parse(b"\0")["Flag_0x0"]
    for val in range(1, 256):
        assert par.parse(bytes([val]))["Flag_0x0"]

    par = fd.ByteFlag(1)
    assert not par.parse(b"\0")["Flag_0x0"]
    assert par.parse(bytes([1]))["Flag_0x0"]
    for val in range(2, 256):
        with pytest.raises(FBError):
            _ = par.parse(bytes([val]))


def test_bit_const():
    par = fd.BitOne
    assert par.parse(b"\x80")["Const_0x0"]
    with pytest.raises(FBError):
        _ = par.parse(b"\x00")
    par = fd.BitZero
    assert not par.parse(b"\x00")["Const_0x0"]
    with pytest.raises(FBError):
        _ = par.parse(b"\x80")


def test_bit_word_const():
    par = fd.BitWordConst(b"\xFF", 3)
    assert par.parse(b"\xF0")["Const_0x0"] == 0x07
    with pytest.raises(FBError):
        _ = par.parse(b"\x80")


def test_bit_flags():
    par = fd.BitFlags(8)
    assert par.parse(b"\x55")["Const_0x0"] == [
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        True,
    ]


def test_int32l():
    par = fd.Int32L
    result = par.parse(struct.pack("<i", -76))
    print(result)
    assert result["Int32_0x0"] == -76


def test_int16l():
    par = fd.Int16L
    assert par.parse(struct.pack("<h", -76))["Int16_0x0"] == -76


def test_int8l():
    par = fd.Int8
    assert par.parse(struct.pack("b", -76))["Int8_0x0"] == -76


def test_uint32l():
    par = fd.UInt32L
    assert par.parse(struct.pack("<I", 1244354))["UInt32_0x0"] == 1244354


def test_uint16l():
    par = fd.UInt16L
    assert par.parse(struct.pack("<H", 12552))["UInt16_0x0"] == 12552


def test_uint8():
    par = fd.UInt8
    assert par.parse(struct.pack("B", 129))["UInt8_0x0"] == 129


def test_float32l():
    dat = struct.pack("<f", 123.4)
    num = struct.unpack("<f", dat)[0]
    par = fd.Float32L
    assert par.parse(dat)["Float32_0x0"] == num


def test_float64l():
    dat = struct.pack("<d", 123.4)
    num = struct.unpack("<d", dat)[0]
    par = fd.Float64L
    assert par.parse(dat)["Float64_0x0"] == num


def test_uuidl():
    u = uuid.uuid4()
    ubytes = u.bytes_le
    par = fd.UuidL
    assert par.parse(ubytes)["UUID_0x0"] == u


def test_uuidb():
    u = uuid.uuid4()
    ubytes = u.bytes
    par = fd.UuidB
    assert par.parse(ubytes)["UUID_0x0"] == u
