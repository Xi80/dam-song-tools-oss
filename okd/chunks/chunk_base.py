from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from typing import BinaryIO


@dataclass
class ChunkBase(ABC):
    """Chunk Base Class"""

    END_OF_FILE_MARK = b"\x00\x00\x00\x00"

    id: bytes

    @staticmethod
    def __descramble_header(id: bytes, size: int) -> tuple[bytes, int]:
        """Descramble Chunk Header

        Args:
            id (bytes): ID
            size (int): Size

        Returns:
            tuple[int, bytes]: ID and Size
        """
        # Scrambled YADD chunk header
        if id == b"\x4e\x96\x53\x93":
            id = b"YADD"
            size ^= 0x17D717D7
        return id, size

    @staticmethod
    def _read_common(stream: BinaryIO) -> tuple[bytes, bytes]:
        """Read Common Part

        Args:
            stream (BinaryIO): Input stream

        Returns:
            tuple[int, bytes]: Chunk ID and Payload
        """
        buffer = stream.read(8)
        if len(buffer) == 0 or buffer == ChunkBase.END_OF_FILE_MARK:
            # End of File
            raise ValueError("Reached to End of File.")
        if len(buffer) != 8:
            stream.seek(-len(buffer), os.SEEK_CUR)
            raise ValueError("Reached to End of File.")
        id = buffer[0:4]
        size = int.from_bytes(buffer[4:8], "big")
        id, size = ChunkBase.__descramble_header(id, size)
        payload = stream.read(size)
        return id, payload

    @staticmethod
    def peek_header(stream: BinaryIO) -> tuple[bytes, int] | None:
        """Peek Header

        Args:
            stream (BinaryIO): Input stream

        Returns:
            bytes: ID and Size
        """
        buffer = stream.read(8)
        stream.seek(-len(buffer), os.SEEK_CUR)
        if len(buffer) == 0 or buffer == ChunkBase.END_OF_FILE_MARK:
            # End of File
            return
        if len(buffer) != 8:
            # End of File
            return
        id = buffer[0:4]
        size = int.from_bytes(buffer[4:8], "big")
        return ChunkBase.__descramble_header(id, size)

    @staticmethod
    def __seek_header(
        stream: BinaryIO, id: bytes | None = None
    ) -> tuple[bytes, int] | None:
        """Seek header

        Args:
            stream (BinaryIO): Input stream
            id (bytes | None, optional): Target ID. Defaults to None.

        Returns:
            tuple[int, int] | None: If ID and size found, else not found
        """
        while True:
            header = ChunkBase.peek_header(stream)
            if header is None:
                return
            current_id, current_size = header
            if id is None:
                return (current_id, current_size)
            else:
                if current_id == id:
                    return (current_id, current_size)
            stream.seek(8 + current_size, os.SEEK_CUR)

    @staticmethod
    def index_chunk(stream: BinaryIO) -> list[tuple[int, int, bytes]]:
        """Index Chunk

        Args:
            stream (BinaryIO): Input stream

        Returns:
            list[tuple[int, int, bytes]]: List of offset, size and ID
        """
        index: list[tuple[int, int, bytes]] = []

        id = b""
        last_position = -1
        while True:
            header = ChunkBase.__seek_header(stream)
            if header is None:
                break
            id, size = header
            position = stream.tell()
            if last_position != -1:
                index.append((last_position, position - last_position, id))
            last_position = position
            stream.seek(8 + size, os.SEEK_CUR)

        if last_position != -1:
            position = stream.tell()
            index.append((last_position, position - last_position, id))

        return index

    @abstractmethod
    def _payload_buffer(self) -> bytes:
        """Payload Buffer

        Returns:
            bytes: Payload Buffer
        """
        pass

    def write(self, stream: BinaryIO) -> None:
        """Write

        Args:
            stream (BinaryIO): Output stream
        """
        payload_buffer = self._payload_buffer()
        stream.write(self.id)
        if len(payload_buffer) % 2 != 0:
            payload_buffer += b"\x00"
        stream.write(len(payload_buffer).to_bytes(4, "big"))
        stream.write(payload_buffer)
