from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Self

from .chunk_base import ChunkBase
from .generic_chunk import GenericChunk


@dataclass
class ExtendedPTrackInfoChannelInfoEntry:
    """Extended P-Track Information Channel Information Entry"""

    attribute: int
    ports: int
    unknown_0: int
    control_change_ax: int
    control_change_cx: int

    @classmethod
    def read(cls, stream: BinaryIO) -> Self:
        """Read

        Args:
            stream (BinaryIO): Input stream

        Returns:
            Self: Instance of this class
        """
        buffer = stream.read(8)
        if len(buffer) < 8:
            raise ValueError("Too less read bytes.")

        attribute = int.from_bytes(buffer[0:2], "little")
        ports = int.from_bytes(buffer[2:4], "big")
        unknown_0 = int.from_bytes(buffer[4:6], "big")
        control_change_ax = buffer[6]
        control_change_cx = buffer[7]
        return cls(attribute, ports, unknown_0, control_change_ax, control_change_cx)

    def is_chorus(self) -> bool:
        """Is Chorus

        Returns:
            bool: True if Chorus, else False
        """
        return self.attribute & 0x0080 != 0x0080

    def is_guide_melody(self) -> bool:
        """Is Guide Melody

        Returns:
            bool: True if Guide Melody, else False
        """
        return self.attribute & 0x0100 == 0x0100

    def write(self, stream: BinaryIO) -> None:
        """Write

        Args:
            stream (BinaryIO): Output stream
        """
        stream.write(self.attribute.to_bytes(2, "little"))
        stream.write(self.ports.to_bytes(2, "big"))
        stream.write(self.unknown_0.to_bytes(2, "big"))
        stream.write(self.control_change_ax.to_bytes())
        stream.write(self.control_change_cx.to_bytes())


@dataclass
class ExtendedPTrackInfoEntry:
    """Extended P-Track Information Entry"""

    track_number: int
    track_status: int
    unused_0: int
    default_channel_groups: list[int]
    channel_groups: list[int]
    channel_info: list[ExtendedPTrackInfoChannelInfoEntry]
    system_ex_ports: int
    unknown_0: int

    @classmethod
    def read(cls, stream: BinaryIO) -> Self:
        """Read

        Args:
            stream (BinaryIO): Input stream

        Returns:
            Self: Instance of this class
        """
        buffer = stream.read(68)
        if len(buffer) < 68:
            raise ValueError("Too less read bytes.")

        track_number = buffer[0]
        track_status = buffer[1]
        unused_0 = int.from_bytes(buffer[2:4], "big")

        default_channel_groups: list[int] = []
        for channel in range(16):
            offset = 4 + 2 * channel
            default_channel_groups.append(
                int.from_bytes(buffer[offset : offset + 2], "big")
            )

        channel_groups: list[int] = []
        for channel in range(16):
            offset = 36 + 2 * channel
            channel_groups.append(int.from_bytes(buffer[offset : offset + 2], "big"))

        channel_info: list[ExtendedPTrackInfoChannelInfoEntry] = []
        for _ in range(16):
            channel_info.append(ExtendedPTrackInfoChannelInfoEntry.read(stream))

        buffer = stream.read(4)
        if len(buffer) < 4:
            raise ValueError("Too less read bytes.")

        system_ex_ports = int.from_bytes(buffer[0:2], "big")
        unknown_0 = int.from_bytes(buffer[2:4], "big")

        return cls(
            track_number,
            track_status,
            unused_0,
            default_channel_groups,
            channel_groups,
            channel_info,
            system_ex_ports,
            unknown_0,
        )

    def is_lossless_track(self) -> bool:
        return self.track_status & 0x80 == 0x80

    def write(self, stream: BinaryIO) -> None:
        """Write

        Args:
            stream (BinaryIO): Output stream
        """
        stream.write(self.track_number.to_bytes())
        stream.write(self.track_status.to_bytes())
        stream.write(self.unused_0.to_bytes(2, "big"))
        for default_channel_group in self.default_channel_groups:
            stream.write(default_channel_group.to_bytes(2, "big"))
        for channel_group in self.channel_groups:
            stream.write(channel_group.to_bytes(2, "big"))
        for channel_info_entry in self.channel_info:
            channel_info_entry.write(stream)
        stream.write(self.system_ex_ports.to_bytes(2, "big"))
        stream.write(self.unknown_0.to_bytes(2, "big"))


@dataclass
class ExtendedPTrackInfoChunk(ChunkBase):
    """Extended P-Track Information Chunk"""

    unknown_0: bytes
    tg_mode: int
    data: list[ExtendedPTrackInfoEntry]

    @classmethod
    def from_generic(cls, generic: GenericChunk) -> Self:
        """From Generic Chunk

        Args:
            generic (GenericChunk): Generic Chunk

        Returns:
            Self: ExtendedPTrackInfoChunk
        """
        unknown_0 = generic.payload[0:8]
        tg_mode = int.from_bytes(generic.payload[8:10], "big")
        entry_count = int.from_bytes(generic.payload[10:12], "big")
        data: list[ExtendedPTrackInfoEntry] = []
        stream = BytesIO(generic.payload[12:])
        for _ in range(entry_count):
            entry = ExtendedPTrackInfoEntry.read(stream)
            data.append(entry)
        return cls(generic.id, unknown_0, tg_mode, data)

    def _payload_buffer(self) -> bytes:
        buffer = self.unknown_0
        buffer += self.tg_mode.to_bytes(2, "big")
        buffer += len(self.data).to_bytes(2, "big")

        stream = BytesIO()
        for entry in self.data:
            entry.write(stream)
        stream.seek(0)
        buffer += stream.read()

        return buffer
