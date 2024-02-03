# format_breaker
The purpose of this library is to extra data fields from arbitrary binary data
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
