from dataclasses import dataclass
from io import BufferedReader, BufferedWriter, BytesIO
from typing import Self

from .chunk_base import ChunkBase
from .generic_chunk import GenericChunk


@dataclass
class PTrackInfoChannelInfoEntry:
    """P-Track Information Channel Information Entry"""

    attribute: int
    ports: int
    control_change_ax: int
    control_change_cx: int

    @classmethod
    def read(cls, stream: BufferedReader) -> Self:
        """Read

        Args:
            stream (BufferedReader): Input stream

        Returns:
            Self: Instance of this class
        """
        buffer = stream.read(4)
        if len(buffer) < 4:
            raise ValueError("Too less read bytes.")

        attribute = buffer[0]
        ports = buffer[1]
        control_change_ax = buffer[2]
        control_change_cx = buffer[3]
        return cls(attribute, ports, control_change_ax, control_change_cx)

    def is_chorus(self) -> bool:
        """Is Chorus

        Returns:
            bool: True if Chorus, else False
        """
        return self.attribute & 0x01 != 0x01

    def is_guide_melody(self) -> bool:
        """Is Guide Melody

        Returns:
            bool: True if Guide Melody, else False
        """

        return self.attribute & 0x80 != 0x80

    def write(self, stream: BufferedWriter) -> None:
        """Write

        Args:
            stream (BufferedReader): Output stream
        """
        stream.write(self.attribute.to_bytes())
        stream.write(self.ports.to_bytes())
        stream.write(self.control_change_ax.to_bytes())
        stream.write(self.control_change_cx.to_bytes())


@dataclass
class PTrackInfoEntry:
    """P-Track Information Entry"""

    track_number: int
    track_status: int
    use_channel_group_flag: int
    default_channel_groups: list[int]
    channel_groups: list[int]
    channel_info: list[PTrackInfoChannelInfoEntry]
    system_ex_ports: int

    @classmethod
    def read(cls, stream: BufferedReader) -> Self:
        """Read

        Args:
            stream (BufferedReader): Input stream

        Returns:
            Self: Instance of this class
        """
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

        channel_info: list[int] = []
        for channel in range(16):
            channel_info.append(PTrackInfoChannelInfoEntry.read(stream))

        buffer = stream.read(2)
        if len(buffer) < 2:
            raise ValueError("Too less read bytes.")

        system_ex_ports = int.from_bytes(buffer[0:2], "little")

        return cls(
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

    def write(self, stream: BufferedWriter) -> None:
        """Write

        Args:
            stream (BufferedReader): Output stream
        """
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


@dataclass
class PTrackInfoChunk(ChunkBase):
    """P-Track Information Chunk"""

    data: list[PTrackInfoEntry]

    @classmethod
    def from_generic(cls, generic: GenericChunk) -> Self:
        """From Generic Chunk

        Args:
            generic (GenericChunk): Generic Chunk

        Returns:
            Self: Instance of this class
        """
        p_track_info: list[PTrackInfoEntry] = []
        entry_count = int.from_bytes(generic.payload[0:2], "big")
        stream = BytesIO(generic.payload[2:])
        for _ in range(entry_count):
            entry = PTrackInfoEntry.read(stream)
            p_track_info.append(entry)
        return cls(generic.id, p_track_info)

    @classmethod
    def from_json_object(
        cls, json_object: object
    ) -> PTrackInfoChannelInfoEntry | PTrackInfoEntry | Self:
        """From JSON Object

        Args:
            json_object (object): JSON Object

        Returns:
            PTrackInfoChannelInfoEntry | PTrackInfoEntry | Self: Converted instance
        """
        if "attribute" in json_object:
            return PTrackInfoChannelInfoEntry(
                json_object["attribute"],
                json_object["ports"],
                json_object["control_change_ax"],
                json_object["control_change_cx"],
            )
        elif "track_number" in json_object:
            return PTrackInfoEntry(
                json_object["track_number"],
                json_object["track_status"],
                json_object["use_channel_group_flag"],
                json_object["default_channel_groups"],
                json_object["channel_groups"],
                json_object["channel_info"],
                json_object["system_ex_ports"],
            )
        elif "data" in json_object:
            return cls(json_object["data"])

    def _payload_buffer(self) -> bytes:
        buffer = len(self.data).to_bytes(2, "big")

        stream = BytesIO()
        for entry in self.data:
            entry.write(stream)
        stream.seek(0)
        buffer += stream.read()

        return buffer
