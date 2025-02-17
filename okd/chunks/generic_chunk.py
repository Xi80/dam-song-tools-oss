from dataclasses import dataclass
from io import BufferedReader
from typing import Self

from . import ChunkBase


@dataclass
class GenericChunk(ChunkBase):
    """Generic Chunk"""

    payload: bytes

    @classmethod
    def read(cls, stream: BufferedReader) -> Self:
        """Read

        Args:
            stream (BufferedReader): Input stream

        Returns:
            Self: Generic Chunk
        """

        id, payload = ChunkBase._read_common(stream)
        return cls(id, payload)

    def _payload_buffer(self) -> bytes:
        return self.payload
