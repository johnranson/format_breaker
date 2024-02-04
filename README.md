# format_breaker
The purpose of this library is to extract data fields from arbitrary binary data
## Library Goals
### Simple and standard outputs
The result of parsing data is a standard python dictionary of field names and the parsed values.
### Human readible declarative syntax
The library doesn't use format strings to define the data. A byte is a Byte.
### Define fields sequentially or by address
Data fields can be given specific addresses. Without address, fields are read sequentially.
### Don't throw away unknown data
Data between known fields is labeled clearly and stored

## Not yet implemented
### Reading from streams
The library currently only supports reading from bytes objects. Long term, it would be convenient to be able to work directly with streams
### Variable length fields
The library currently only supports fixed length fields. We plan to add a couple mechanisms for variable length fields.
### Writing
The library currently only supports reading data. It is a goal to be able to take a dictionary and generate binary data.

## Code Examples


```
>>>import pprint
>>>import struct
>>>import format_breaker as fb

>>>pp = pprint.PrettyPrinter(indent=4)

>>>dat = struct.pack("<d", 45.23)
>>>pp.pprint(fb.Float64l("fnum").parse(dat))

{'fnum': 45.23}
```
```
>>>dat = struct.pack("<d", 45.23) + struct.pack("<d", 21.23)
>>>fmt = fb.Chunk(fb.Float64l("fnum1"), fb.Float64l("fnum2"))
>>>pp.pprint(fmt.parse(dat))

{'fnum1': 45.23, 'fnum2': 21.23}
```


```
>>>dat = struct.pack("<d", 45.23) + b'\0' * 120 + struct.pack("<d", 21.23)
>>>fmt = fb.Chunk(fb.Float64l("fnum1"), fb.Float64l("fnum2",128))
>>>pp.pprint(fmt.parse(dat))

{   'fnum1': 45.23,
    'fnum2': 21.23,
    'spacer_0x8-0x7f': b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                       b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'}
```

```
integer_val = 14768

arr = (
    bytes(range(154))
    + integer_val.to_bytes(4, "little")
    + struct.pack("<f", 45.23)
    + struct.pack("<d", 45.23)
    + bytes(range(10))
)

arr = arr + arr + b"\0\0\0"

record_format = fb.Chunk(
    fb.Byte("byte_0"),
    fb.Byte("byte_100", 100),
    fb.Byte("byte_150", 150),
    fb.Bytes(3)("bytes_151"),
    fb.Int32sl("int_154"),
    fb.Float32l("float_158"),
    fb.Float64l("float_158"),
    fb.PadToAddress(180),
    relative=True,
)

overall_format = fb.Chunk(
    record_format("First_chunk"),
    record_format("Second_chunk"),
    fb.Remnant()
    )

pp.pprint(overall_format.parse(arr))
```
```
{   'First_chunk': {   'byte_0': b'\x00',
                       'byte_100': b'd',
                       'byte_150': b'\x96',
                       'bytes_151': b'\x97\x98\x99',
                       'float_158': 45.22999954223633,
                       'float_158 1': 45.23,
                       'int_154': 14768,
                       'spacer_0x1-0x63': b'\x01\x02\x03\x04\x05\x06\x07\x08'
                                          b'\t\n\x0b\x0c\r\x0e\x0f\x10'
                                          b'\x11\x12\x13\x14\x15\x16\x17\x18'
                                          b'\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$'
                                          b"%&'()*+,-./0123456789:;<=>?@ABCD"
                                          b'EFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abc',
                       'spacer_0x65-0x95': b'efghijklmnopqrstuvwxyz{|}~\x7f\x80'
                                           b'\x81\x82\x83\x84\x85\x86\x87\x88'
                                           b'\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90'
                                           b'\x91\x92\x93\x94\x95',
                       'spacer_0xaa-0xb3': b'\x00\x01\x02\x03\x04\x05\x06\x07'
                                           b'\x08\t'},
    'Second_chunk': {   'byte_0': b'\x00',
                        'byte_100': b'd',
                        'byte_150': b'\x96',
                        'bytes_151': b'\x97\x98\x99',
                        'float_158': 45.22999954223633,
                        'float_158 1': 45.23,
                        'int_154': 14768,
                        'spacer_0x1-0x63': b'\x01\x02\x03\x04\x05\x06\x07\x08'
                                           b'\t\n\x0b\x0c\r\x0e\x0f\x10'
                                           b'\x11\x12\x13\x14\x15\x16\x17\x18'
                                           b'\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$'
                                           b"%&'()*+,-./0123456789:;<=>?@ABCD"
                                           b'EFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abc',
                        'spacer_0x65-0x95': b'efghijklmnopqrstuvwxyz{|'
                                            b'}~\x7f\x80\x81\x82\x83\x84'
                                            b'\x85\x86\x87\x88\x89\x8a\x8b\x8c'
                                            b'\x8d\x8e\x8f\x90\x91\x92\x93\x94'
                                            b'\x95',
                        'spacer_0xaa-0xb3': b'\x00\x01\x02\x03\x04\x05\x06\x07'
                                            b'\x08\t'},
    'remnant_0x168': b'\x00\x00\x00'}
```
