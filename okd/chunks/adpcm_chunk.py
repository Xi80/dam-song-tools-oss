from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Self

from ..adpcm import AdpcmDecoder

from .chunk_base import ChunkBase
from .generic_chunk import GenericChunk


@dataclass
class AdpcmChunkTrack:
    """ADPCM Chunk"""

    TRACK_ID = b"YAWV"

    data: bytes

    def decode(self) -> list[int]:
        """Decode

        Returns:
            list[int]: Decoded samples
        """
        stream = BytesIO(self.data)
        decoder = AdpcmDecoder()
        return decoder.decode(stream)

    def write(self, stream: BinaryIO) -> None:
        """Write

        Args:
            stream (BufferedReader): Output stream
        """
        stream.write(AdpcmChunkTrack.TRACK_ID)
        stream.write(len(self.data).to_bytes(4, "big"))
        stream.write(self.data)


@dataclass
class AdpcmChunk(ChunkBase):
    """ADPCM Chunk"""

    tracks: list[AdpcmChunkTrack]

    @classmethod
    def from_generic(cls, generic: GenericChunk) -> Self:
        """From Generic Chunk

        Args:
            generic (GenericChunk): Generic Chunk

        Returns:
            Self: Instance of this class
        """
        stream = BytesIO(generic.payload)
        tracks: list[AdpcmChunkTrack] = []
        while True:
            buffer = stream.read(8)
            if len(buffer) < 8:
                break

            chunk_id = buffer[0:4]
            if chunk_id == AdpcmChunkTrack.TRACK_ID:
                chunk_size = int.from_bytes(buffer[4:8], "big")
                chunk_data = stream.read(chunk_size)
                if len(chunk_data) < chunk_size:
                    raise ValueError("Too less read bytes.")
                tracks.append(AdpcmChunkTrack(chunk_data))
            else:
                raise ValueError(f"Unknown Chunk ID detected. chunk_id=`{chunk_id}`")

        return cls(generic.id, tracks)

    def _payload_buffer(self) -> bytes:
        buffer = b""
        for track in self.tracks:
            buffer += track.data
        return buffer
