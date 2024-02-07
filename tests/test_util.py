import pytest
from formatbreaker.util import *


def test_uniquify_name():
    context = {}

    assert uniquify_name("name", context) == "name"

    context = {"name": 2}

    assert uniquify_name("name", context) == "name 1"

    context.update({"name 1": 2})

    assert uniquify_name("name", context) == "name 2"


def test_spacer():

    data = bytes(range(100))

    context = {}

    result = spacer(data, context, 1, 5)

    assert result == 6
    assert context["spacer_0x1-0x5"] == data[1:6]

    result = spacer(data, context, 1, 5)
    assert result == 6
    assert context["spacer_0x1-0x5 1"] == data[1:6]

    result = spacer(data, context, 0, 100)
    assert result == 100
    assert context["spacer_0x0-0x63"] == data

    with pytest.raises(IndexError):
        result = spacer(data, context, 0, 101)

    with pytest.raises(IndexError):
        result = spacer(data, context, -1, 5)

    with pytest.raises(IndexError):
        result = spacer(data, context, 1000, 1)

    result = spacer(data, context, 1, 0)
    assert result == 1

    with pytest.raises(ValueError):
        result = spacer(data, context, 1, -1)


def test_bitwise_bytes():
    bytedata = b"\xff\x0f\x00\xff"
    data = BitwiseBytes(bytedata)
    assert bytes(data) == bytedata

    assert data[0:8] == data[24:32]

    assert data[0:8] != data[8:16]

    assert data[0:9] != data[24:32]

    assert data[-50:200] == data

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

    assert len(data) == 32

    assert int(data) == 4279173375

    with pytest.raises(IndexError):
        data[32]

    with pytest.raises(IndexError):
        data[-33]

    with pytest.raises(NotImplementedError):
        data[1:10:2]

    with pytest.raises(NotImplementedError):
        data[1:10:-1]

    for i in range(32):
        assert data[-1 - i] == data[31 - i]

    assert bytes(data[:0]) == b""

    assert data[:0] == BitwiseBytes(b"")

    data = BitwiseBytes(b"")

    assert len(data) == 0
    assert bytes(data) == b""

    assert not data.to_bools()
