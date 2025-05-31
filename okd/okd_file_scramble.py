from logging import getLogger
from random import randint
from typing import BinaryIO

from .okd_scramble_pattern import OKD_SCRAMBLE_PATTERN

__logger = getLogger(__name__)


def choose_scramble_pattern_index():
    return randint(0x00, 0xFF)


def scramble(
    input_stream: BinaryIO,
    output_stream: BinaryIO,
    scramble_pattern_index: int,
    length: int | None = None,
):
    """Scramble

    Args:
        input_stream (BinaryIO): Input stream
        output_stream (BinaryIO): Output stream
        scramble_pattern_index (int): Scramble pattern index
        length (int | None, optional): Length. Defaults to None.

    Returns:
        int: Last scramble pattern index
    """
    if length is not None and length % 2 != 0:
        raise ValueError("Argument `length` length must be multiple of 2.")

    start_position = input_stream.tell()
    while length is None or (
        length is not None and (input_stream.tell() - start_position) < length
    ):
        plaintext_buffer = input_stream.read(2)
        if len(plaintext_buffer) == 0:
            if length is None:
                break
            else:
                raise RuntimeError("Reached to unexpected End of Stream.")
        if len(plaintext_buffer) % 2 != 0:
            raise ValueError("`plaintext_buffer` length must be 2.")
        plaintext = int.from_bytes(plaintext_buffer, "big")
        scramble_pattern = OKD_SCRAMBLE_PATTERN[scramble_pattern_index % 0x100]
        scrambled = plaintext ^ scramble_pattern
        scrambled_buffer = scrambled.to_bytes(2, "big")
        output_stream.write(scrambled_buffer)
        scramble_pattern_index += 1
    return scramble_pattern_index % 0x100


def detect_scramble_pattern_index(
    stream: BinaryIO,
    expected_magic_bytes: bytes,
) -> int | None:
    """Detect scramble pattern index

    Args:
        stream (BinaryIO): Input stream
        expected_magic_bytes (bytes): Expected magic bytes (4 bytes)

    Raises:
        ValueError: Invalid argument `expected_magic_bytes`
        RuntimeError: Failed to detect OKD file `scramble_pattern_index`

    Returns:
        int | None: Scrambled pattern index if int, unscrambled if None
    """
    if len(expected_magic_bytes) != 4:
        raise ValueError("Argument `expected_magic_bytes` length must be 4.")

    expected_magic_bytes_int = int.from_bytes(expected_magic_bytes, "big")

    position = stream.tell()
    magic_bytes_buffer = stream.read(4)
    stream.seek(position)
    if len(magic_bytes_buffer) != 4:
        raise RuntimeError("Invalid `magic_bytes_buffer` length.")
    magic_bytes_int = int.from_bytes(magic_bytes_buffer, "big")
    if magic_bytes_int == expected_magic_bytes_int:
        __logger.info("OKD file is not scrambled.")
        return

    __logger.info("OKD file is scrambled.")
    expected_pattern = magic_bytes_int ^ expected_magic_bytes_int
    for scramble_pattern_index in range(0x100):
        if scramble_pattern_index == 0xFF:
            candidated_pattern = OKD_SCRAMBLE_PATTERN[0]
        else:
            candidated_pattern = OKD_SCRAMBLE_PATTERN[scramble_pattern_index + 1]
        candidated_pattern |= OKD_SCRAMBLE_PATTERN[scramble_pattern_index] << 16
        if candidated_pattern == expected_pattern:
            __logger.info(
                f"OKD file `scramble_pattern_index` detected. scramble_pattern_index={scramble_pattern_index}"
            )
            return scramble_pattern_index
    raise RuntimeError("Failed to detect OKD file `scramble_pattern_index`.")


def descramble(
    input_stream: BinaryIO,
    output_stream: BinaryIO,
    scramble_pattern_index: int,
    length: int | None = None,
) -> int:
    """Descramble

    Args:
        input_stream (BinaryIO): Input stream
        output_stream (BinaryIO): Output stream
        scramble_pattern_index (int): Scramble pattern index
        length (int | None, optional): Length. Defaults to None.

    Returns:
        int: Last scramble pattern index
    """
    if length is not None and length % 2 != 0:
        raise ValueError("Argument `length` length must be multiple of 2.")

    start_position = input_stream.tell()
    while length is None or (
        length is not None and (input_stream.tell() - start_position) < length
    ):
        scrambled_buffer = input_stream.read(2)
        if len(scrambled_buffer) == 0:
            if length is None:
                break
            else:
                raise RuntimeError("Reached to unexpected End of Stream.")
        if len(scrambled_buffer) % 2 != 0:
            raise ValueError("`plaintext_buffer` length must be 2.")
        scrambled = int.from_bytes(scrambled_buffer, "big")
        scramble_pattern = OKD_SCRAMBLE_PATTERN[scramble_pattern_index % 0x100]
        plaintext = scrambled ^ scramble_pattern
        plaintext_buffer = plaintext.to_bytes(2, "big")
        output_stream.write(plaintext_buffer)
        scramble_pattern_index = scramble_pattern_index + 1
    return scramble_pattern_index % 0x100
