import pprint
import format_breaker as fb
import struct

pp = pprint.PrettyPrinter(indent=4)

dat = struct.pack("<d", 45.23)
pp.pprint(fb.Float64l("fnum").parse(dat))

print()

dat = struct.pack("<d", 45.23) + struct.pack("<d", 21.23)
fmt = fb.Chunk(fb.Float64l("fnum1"), fb.Float64l("fnum2"))
pp.pprint(fmt.parse(dat))


dat = struct.pack("<d", 45.23) + b'\0' * 120 + struct.pack("<d", 21.23)
fmt = fb.Chunk(fb.Float64l("fnum1"), fb.Float64l("fnum2",128))
pp.pprint(fmt.parse(dat))


# integer_val = 14768

# arr = (
#     bytes(range(154))
#     + integer_val.to_bytes(4, "little")
#     + struct.pack("<f", 45.23)
#     + struct.pack("<d", 45.23)
#     + bytes(range(10))
# )

# arr = arr + arr + b"\0\0\0"

# a = fb.Chunk(
#     fb.Byte("byte_0"),
#     fb.Byte("byte_100", 100),
#     fb.Byte("byte_150", 150),
#     fb.Bytes(3)("bytes_151"),
#     fb.Int32sl("int_154"),
#     fb.Float32l("float_158"),
#     fb.Float64l("float_158"),
#     fb.PadToAddress(180),
#     relative=True,
# )

# b = fb.Chunk(a, a("Second_chunk"), fb.Remnant())

# # Note first chunk is unnamed and stores directly in containing context

# pp.pprint(b.parse(arr))
