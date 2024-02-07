"""Code that is mostly used internally"""

from operator import add


def uniquify_name(name, context):
    """This adds " N" to a string key if the key already exists in the
        dictionary, where N is the first natural number that makes the
        key unique

    Args:
        name (string): A string
        context (dictionary): Any dictionary

    Returns:
        string: A unique string key
    """
    new_name = name
    i = 1
    while new_name in context:
        new_name = name + " " + str(i)
        i = i + 1
    return new_name


def spacer(data, context, addr, spacer_size):
    """Reads a spacer of a certain length from the data, and saves it
        to the context dictionary

    Args:
        data (bytes or BitwiseBytes): Data being parsed
        context (dict): The dictionary where results are stored
        abs_addr (int): The current absolute bit or byte address in the data
        spacer_size (_type_): The size in bits or bytes of the spacer

    Returns:
        abs_addr (int): The bit or byte address following the spacer
    """
    end_addr = addr + spacer_size

    if spacer_size < 1:
        raise ValueError
    if spacer_size > 1:
        spacer_name = "spacer_" + hex(addr) + "-" + hex(addr + spacer_size - 1)
    else:
        spacer_name = "spacer_" + hex(addr)

    spacer_name = uniquify_name(spacer_name, context)

    context[spacer_name] = bytes(data[addr:end_addr])

    return end_addr


class BitwiseBytes:
    """Allows treating bytes as a subscriptable bit list"""

    def __init__(self, value, start_byte=0, start_bit=0, length=None):
        self.data = bytes(value)
        self.start_byte = start_byte
        self.start_bit = start_bit
        if length:
            self.length = length
        else:
            self.length = len(value) * 8

        self.stop_bit = self.length % 8 + start_bit
        self.stop_byte = self.length // 8 + start_byte
        if self.stop_bit > 7:
            self.stop_byte += 1
            self.stop_bit -= 8

    def __getitem__(self, item):
        if isinstance(item, slice):
            start, stop, step = item.indices(self.length)
            length = stop - start
            if step != 1:
                raise NotImplementedError
            start_bit = (self.start_bit + start % 8) % 8
            start_byte = self.start_byte + (start + self.start_bit) // 8

            return BitwiseBytes(self.data, start_byte, start_bit, length)

        elif isinstance(item, int):
            if item >= self.length:
                raise IndexError
            bit_ind = (self.start_bit + item % 8) % 8
            byte_ind = self.start_byte + (item + self.start_bit) // 8

            bit_raw = (0x80 >> bit_ind) & self.data[byte_ind]

            return bool(bit_raw)

        else:
            raise ValueError

    def __len__(self):
        return self.length

    def __bytes__(self):

        if self.stop_bit == 0:
            last_byte_addr = self.stop_byte - 1
        else:
            last_byte_addr = self.stop_byte

        single_byte = last_byte_addr == self.start_byte
        multi_byte = last_byte_addr > self.start_byte + 1

        stop_shift = (8 - self.stop_bit) % 8

        if single_byte:
            result = bytes(
                [(self.data[self.start_byte] & (0xFF >> self.start_bit)) >> stop_shift]
            )
        else:
            first_byte = bytes([self.data[self.start_byte] & (0xFF >> self.start_bit)])
            last_byte = bytes([self.data[last_byte_addr] & (0xFF << stop_shift)])
            mid_bytes = b""
            if multi_byte:
                mid_bytes = self.data[self.start_byte + 1 : last_byte_addr]

            data = first_byte + mid_bytes + last_byte

            shift_data = [b << (8 - stop_shift) for b in data]

            first_part = [b & 0xFF for b in shift_data[:-1]]
            second_part = [b >> 8 for b in shift_data[1:]]

            result = bytes(map(add, first_part, second_part))
        return result

    def to_bools(self):
        return [self[i] for i in range(self.length)]

    def __index__(self):
        return int.from_bytes(bytes(self), "big", signed=False)

    def __eq__(self, other):
        return (self.length == other.length) and (int(self) == int(other))
