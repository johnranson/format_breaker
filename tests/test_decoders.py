# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access

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
    par = fd.BitConst(True)
    assert par.parse(b"\x80")["Const_0x0"]
    with pytest.raises(FBError):
        _ = par.parse(b"\x00")
    par = fd.BitConst(False)
    assert not par.parse(b"\x00")["Const_0x0"]
    with pytest.raises(FBError):
        _ = par.parse(b"\x80")
