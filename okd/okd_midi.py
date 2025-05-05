from io import BufferedReader
import os


def read_status_byte(stream: BufferedReader) -> int:
    """Read Status Byte

    Args:
        stream (BufferedReader): Input stream

    Raises:
        ValueError: Invalid Status Byte

    Returns:
        int: Status Byte
    """
    byte = stream.read(1)
    if len(byte) < 1:
        raise ValueError("Too less read bytes.")
    byte = byte[0]
    if byte & 0x80 != 0x80:
        position = stream.tell()
        raise ValueError(f"Invalid status byte. byte={byte} position={position}")
    return byte


def peek_status_byte(stream: BufferedReader) -> int:
    """Peek Status Byte

    Args:
        stream (BufferedReader): Input stream

    Raises:
        ValueError: Invalid Status Byte

    Returns:
        int: Status Byte
    """
    byte = stream.read(1)
    if len(byte) < 1:
        raise ValueError("Too less read bytes.")
    stream.seek(-1, os.SEEK_CUR)
    byte = byte[0]
    if byte & 0x80 != 0x80:
        position = stream.tell()
        raise ValueError(f"Invalid Status Byte. byte={byte} position={position}")
    return byte


def read_data_byte(stream: BufferedReader) -> int:
    """Read Data Byte

    Args:
        stream (BufferedReader): Input stream

    Raises:
        ValueError: Invalid Data Byte

    Returns:
        int: Data Byte
    """
    byte = stream.read(1)
    if len(byte) < 1:
        raise ValueError("Too less read bytes.")
    byte = byte[0]
    if byte & 0x80 == 0x80:
        position = stream.tell()
        raise ValueError(f"Invalid Data Byte. byte={byte} position={position}")
    return byte


def peek_data_byte(stream: BufferedReader) -> int:
    """Peek Data Byte

    Args:
        stream (BufferedReader): Input stream

    Raises:
        ValueError: Invalid data byte

    Returns:
        int: Data Byte
    """
    byte = stream.read(1)
    if len(byte) < 1:
        raise ValueError("Too less read bytes.")
    stream.seek(-1, os.SEEK_CUR)
    byte = byte[0]
    if byte & 0x80 == 0x80:
        position = stream.tell()
        raise ValueError(f"Invalid data byte. byte={byte} position={position}")
    return byte


def is_data_bytes(data: bytes) -> bool:
    """Is Data Bytes

    Args:
        data (bytes): Data

    Returns:
        bool: True if Data Bytes, else False
    """
    for byte in data:
        if byte & 0x80 == 0x80:
            return False
    return True


def read_variable_int(stream: BufferedReader) -> int:
    """Read Variable Int

    Args:
        stream (BufferedReader): Input stream

    Raises:
        ValueError: Invalid byte sequence

    Returns:
        int: Variable Int value
    """
    value = 0
    for i in range(3):
        byte: int = read_data_byte(stream)
        value += byte << (i * 6)
        if byte & 0x40 != 0x40:
            return value

    position = stream.tell()
    raise ValueError(f"Invalid byte sequence. position={position}")


def write_variable_int(stream: BufferedReader, value: int) -> None:
    """Write Variable Int

    Args:
        stream (BufferedReader): Output stream
        value (int): Value

    Raises:
        ValueError: Invalid argument `value`
    """
    if 0x04103F < value:
        raise ValueError("Too big argument `value`. Use write_extended_variable_int.")

    for i in range(3):
        masked_value = value & (0x3F << (i * 6))
        byte = masked_value >> (i * 6)
        next_value = value - masked_value
        if next_value != 0x000000:
            byte |= 0x40
            next_value -= 0x40 << (i * 6)
        value = next_value
        stream.write(byte.to_bytes())

        if value == 0x000000:
            if byte & 0x40 == 0x40:
                stream.write(b"\x00")
            break


def read_extended_variable_int(stream: BufferedReader) -> int:
    """Read Extended Variable Int

    Args:
        stream (BufferedReader): Input stream

    Returns:
        int: Extended Variable Int value
    """
    value = 0
    while True:
        try:
            byte = peek_data_byte(stream)
            if byte == 0x00:
                # Maybe End of Track
                return value
        except ValueError:
            break
        value += read_variable_int(stream)
    return value


def write_extended_variable_int(stream: BufferedReader, value: int) -> None:
    """Write Extended Variable Int

    Args:
        stream (BufferedReader): Output stream
        value (int): Value
    """
    while 0x000000 < value:
        write_value = min(value, 0x04103F)
        write_variable_int(stream, write_value)
        value -= write_value
