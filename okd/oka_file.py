from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Self

from .okd_file_scramble import descramble


@dataclass
class OkaHeader:
    """OKA Header"""

    MAGIC_BYTES = b"YOKA"
    FIXED_PART_LENGTH = 40

    magic_bytes: bytes
    length: int
    version: str
    id_karaoke: int
    data_offset: int
    unknown_0: int
    crc: int

    @classmethod
    def read(
        cls,
        stream: BinaryIO,
        scramble_pattern_index: int | None = None,
    ) -> Self:
        """Read

        Args:
            stream (BinaryIO): Input stream
            scramble_pattern_index (int): Scramble pattern index

        Raises:
            ValueError: Invalid `magic_bytes`

        Returns:
            Self: Instance of this class
        """
        if scramble_pattern_index is None:
            buffer = stream.read(OkaHeader.FIXED_PART_LENGTH)
        else:
            header_stream = BytesIO()
            scramble_pattern_index = descramble(
                stream,
                header_stream,
                scramble_pattern_index,
                OkaHeader.FIXED_PART_LENGTH,
            )
            header_stream.seek(0)
            buffer = header_stream.read()
        if len(buffer) < OkaHeader.FIXED_PART_LENGTH:
            raise ValueError("Too less read bytes.")

        magic_bytes = buffer[0:4]
        if magic_bytes != OkaHeader.MAGIC_BYTES:
            raise ValueError("Invalid `magic_bytes`.")
        length = int.from_bytes(buffer[4:8], "big")
        version = buffer[8:24].decode("ascii")
        id_karaoke = int.from_bytes(buffer[24:28], "big")
        data_offset = int.from_bytes(buffer[28:32], "big")
        unknown_0 = int.from_bytes(buffer[32:36], "big")
        crc = int.from_bytes(buffer[36:40], "big")
        return cls(
            magic_bytes, length, version, id_karaoke, data_offset, unknown_0, crc
        )

    def write(self, stream: BinaryIO) -> None:
        """Write

        Args:
            stream (BinaryIO): Output stream
        """
        stream.write(OkaHeader.MAGIC_BYTES)
        stream.write(self.length.to_bytes(4, "big"))
        stream.write(self.version.encode("ascii").ljust(16, b"\x00"))
        stream.write(self.id_karaoke.to_bytes(4, "big"))
        stream.write(self.data_offset.to_bytes(4, "big"))
        stream.write(self.unknown_0.to_bytes(4, "big"))
        stream.write(self.crc.to_bytes(4, "big"))
