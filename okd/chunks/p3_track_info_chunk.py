from dataclasses import dataclass
from io import BytesIO
from typing import Self

from .chunk_base import ChunkBase
from .generic_chunk import GenericChunk
from .p_track_info_chunk import PTrackInfoChannelInfoEntry


@dataclass
class P3TrackInfoChannelInfoEntry(PTrackInfoChannelInfoEntry):
    """P3-Track Information Channel Information Entry"""


@dataclass
class P3TrackInfoChunk(ChunkBase):
    """P3-Track Information Chunk"""

    track_number: int
    track_status: int
    use_channel_group_flag: int
    default_channel_groups: list[int]
    channel_groups: list[int]
    channel_info: list[PTrackInfoChannelInfoEntry]
    system_ex_ports: int

    @classmethod
    def from_generic(cls, generic: GenericChunk) -> Self:
        """From Generic Chunk

        Args:
            generic (GenericChunk): Generic Chunk

        Returns:
            Self: Instance of this class
        """
        stream = BytesIO(generic.payload)

        buffer = stream.read(4)
        if len(buffer) < 4:
            raise ValueError("Too less read bytes.")

        track_number = buffer[0]
        track_status = buffer[1]
        use_channel_group_flag = int.from_bytes(buffer[2:4], "big")

        default_channel_groups: list[int] = []
        for channel in range(16):
            if (use_channel_group_flag >> channel) & 0x0001 == 0x0001:
                buffer = stream.read(2)
                if len(buffer) < 2:
                    raise ValueError("Too less read bytes.")

                default_channel_groups.append(int.from_bytes(buffer, "big"))
            else:
                default_channel_groups.append(0x0000)

        buffer = stream.read(32)
        if len(buffer) < 32:
            raise ValueError("Too less read bytes.")

        channel_groups: list[int] = []
        for channel in range(16):
            offset = 2 * channel
            channel_groups.append(int.from_bytes(buffer[offset : offset + 2], "big"))

        channel_info: list[PTrackInfoChannelInfoEntry] = []
        for channel in range(16):
            channel_info.append(PTrackInfoChannelInfoEntry.read(stream))

        buffer = stream.read(2)
        if len(buffer) < 2:
            raise ValueError("Too less read bytes.")

        system_ex_ports = int.from_bytes(buffer[0:2], "big")

        return cls(
            generic.id,
            track_number,
            track_status,
            use_channel_group_flag,
            default_channel_groups,
            channel_groups,
            channel_info,
            system_ex_ports,
        )

    def is_lossless_track(self) -> bool:
        return self.track_status & 0x80 == 0x80

    def _payload_buffer(self) -> bytes:
        """Write

        Args:
            stream (BufferedReader): Output stream
        """
        stream = BytesIO()

        stream.write(self.track_number.to_bytes())
        stream.write(self.track_status.to_bytes())
        stream.write(self.use_channel_group_flag.to_bytes(2, "big"))
        for channel, default_channel_group in enumerate(self.default_channel_groups):
            if (self.use_channel_group_flag >> channel) & 0x0001 != 0x0001:
                continue
            stream.write(default_channel_group.to_bytes(2, "big"))
        for channel_group in self.channel_groups:
            stream.write(channel_group.to_bytes(2, "big"))
        for channel_info_entry in self.channel_info:
            channel_info_entry.write(stream)
        stream.write(self.system_ex_ports.to_bytes(2, "little"))

        stream.seek(0)
        return stream.read()
