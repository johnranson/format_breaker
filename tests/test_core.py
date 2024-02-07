import pytest
from formatbreaker.core import DataType, FBError


def test_data_type():

    test_type = DataType()

    assert test_type.name is None
    assert test_type.address is None

    context = {}

    with pytest.raises(RuntimeError):
        test_type._store(context, "123")

    copy_test_type = test_type()

    assert copy_test_type is not test_type

    assert copy_test_type.name is None
    assert copy_test_type.address is None

    with pytest.raises(ValueError):
        test_type = DataType("name", "address")

    with pytest.raises(ValueError):
        test_type = DataType(3, 3)

    test_type = DataType("name", 3)

    assert test_type.name == "name"
    assert test_type.address == 3

    copy_test_type = test_type()

    assert copy_test_type is not test_type

    assert copy_test_type.name == "name"
    assert copy_test_type.address == 3

    assert test_type._decode("123") == "123"

    context = {}
    test_type._store(context, "123")
    test_type._store(context, "456")
    test_type._update(context, {"test": "123"})
    test_type._update(context, {"test": "456"})
    test_type._update(context, {})

    assert context["name"] == "123"
    assert context["name 1"] == "456"
    assert context["test"] == "123"
    assert context["test 1"] == "456"

    context = {}
    result = test_type._parse(b"123", context, 5)

    assert result is 5
    assert not bool(context)

    with pytest.raises(FBError):
        result = test_type._space_and_parse(b"123456", context, 5)

    result = test_type._space_and_parse(b"123456", context, 3)

    assert result == 3
    assert not bool(context)

    result = test_type._space_and_parse(b"123456", context, 1)

    print(context)

    assert result == 3
    assert context["spacer_0x1-0x2"] == b"23"
