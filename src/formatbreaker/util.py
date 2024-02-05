"""Code that is mostly used internally"""


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


def spacer(data, context, addr, spacer_size, bitwise=False):
    if bitwise:
        return bit_spacer(data, context, addr, spacer_size)
    else:
        return byte_spacer(data, context, addr, spacer_size)


def byte_spacer(data, context, addr, spacer_size):
    """Reads a spacer of a certain length from the data, and saves it
        to the context dictionary

    Args:
        data (bytes): Data being parsed
        context (dict): The dictionary where results are stored
        abs_addr (int): The current absolute byte address in the data
        rel_addr (int): The current relative byte address in the
            current data chunk
        spacer_size (_type_): The size in bytes of the spacer

    Returns:
        abs_addr (int): The absolute byte address following the spacer
        rel_addr (int): The relative byte address in the
            current data chunk following the spacer
    """
    end_addr = addr + spacer_size

    if spacer_size > 1:
        spacer_name = "spacer_" + hex(addr) + "-" + hex(addr - 1)
    else:
        spacer_name = "spacer_" + hex(addr)

    spacer_name = uniquify_name(spacer_name, context)

    context[spacer_name] = data[addr:end_addr]

    return end_addr


def bit_spacer(data, context, addr, spacer_size):
    pass