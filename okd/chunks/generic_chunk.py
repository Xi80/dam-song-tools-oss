from dataclasses import dataclass
from typing import BinaryIO, Self

from .chunk_base import ChunkBase


@dataclass
class GenericChunk(ChunkBase):
    """Generic Chunk"""

    payload: bytes

    @classmethod
    def read(cls, stream: BinaryIO) -> Self:
        """Read

        Args:
            stream (BinaryIOBufferedReader): Input stream

        Returns:
            Self: Generic Chunk
        """
        id, payload = ChunkBase._read_common(stream)
        return cls(id, payload)

    def _payload_buffer(self) -> bytes:
        return self.payload
