"""This contains all custom exceptions used in the package"""


class FBError(Exception):
    """This error should be raised when a Parser fails to parse the data
    because it doesn't fit expectations. The idea is that optional data
    types can fail to be parsed, and the top level code will catch the
    exception and try something else.
    """


class FBNoDataError(FBError):
    """This error should be raised when a Parser tries to read past the
    end of the input data."""
