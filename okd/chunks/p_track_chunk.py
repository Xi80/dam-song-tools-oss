from dataclasses import dataclass
from io import BufferedReader, BufferedWriter, BytesIO
import os
from typing import Self

from midi.event import MidiEvent, MidiTrackEvent
from ..okd_midi import (
    read_status_byte,
    is_data_bytes,
    read_variable_int,
    read_extended_variable_int,
    write_variable_int,
    write_extended_variable_int,
)

from .chunk_base import ChunkBase
from .generic_chunk import GenericChunk
from .p_track_info_chunk import PTrackInfoEntry, PTrackInfoChunk
from .extended_p_track_info_chunk import (
    ExtendedPTrackInfoEntry,
    ExtendedPTrackInfoChunk,
)
from .p3_track_info_chunk import P3TrackInfoChunk


@dataclass
class PTrackEvent(MidiTrackEvent):
    """P-Track Event"""

    __END_OF_TRACK_MARK = b"\x00\x00\x00\x00"

    duration: int | None = None

    @staticmethod
    def read_sysex_data_bytes(stream: BufferedReader) -> bytes:
        """Read Data Bytes of SysEx Message

        Args:
            stream (BufferedReader): Input stream

        Raises:
            ValueError: Unterminated SysEx message detected

        Returns:
            bytes: Data Bytes
        """
        data_bytes = b""
        while True:
            byte = stream.read(1)
            if len(byte) < 1:
                raise ValueError("Too less read bytes.")
            data_bytes += byte
            byte = byte[0]
            if byte & 0x80 == 0x80:
                if byte != 0xF7:
                    raise ValueError(
                        f"Unterminated SysEx message detected. stop_byte={hex(byte)}"
                    )
                break
        return data_bytes

    @classmethod
    def read(cls, stream: BufferedReader) -> Self:
        delta_time = read_extended_variable_int(stream)

        end_of_track = stream.read(4)
        if end_of_track == PTrackEvent.__END_OF_TRACK_MARK:
            return None
        stream.seek(-4, os.SEEK_CUR)

        status_byte = read_status_byte(stream)
        status_type = status_byte & 0xF0

        # Channel voice messages
        if status_type == 0x80:
            # Note off
            data_bytes_length = 3
        elif status_type == 0x90:
            # Note on
            data_bytes_length = 2
        elif status_type == 0xA0:
            # Alternative CC AX
            data_bytes_length = 1
        elif status_type == 0xB0:
            # Control change
            data_bytes_length = 2
        elif status_type == 0xC0:
            # Alternative CC CX
            data_bytes_length = 1
        elif status_type == 0xD0:
            # Channel pressure
            data_bytes_length = 1
        elif status_type == 0xE0:
            # Pitch bend
            data_bytes_length = 2
        # System messages
        elif status_byte == 0xF0:
            # SysEx message
            data_bytes = PTrackEvent.read_sysex_data_bytes(stream)
            return cls(status_byte, data_bytes, delta_time)
        elif status_byte == 0xF8:
            # ADPCM note on
            data_bytes_length = 3
        elif status_byte == 0xF9:
            # Unknown
            data_bytes_length = 1
        elif status_byte == 0xFA:
            # ADPCM channel volume
            data_bytes_length = 1
        elif status_byte == 0xFD:
            # Enable channel grouping
            data_bytes_length = 0
        elif status_byte == 0xFE:
            # Compensation of Alternative CC
            byte = stream.read(1)
            if len(byte) < 1:
                raise ValueError("Too less read bytes.")
            stream.seek(-1, os.SEEK_CUR)
            byte = byte[0]
            if byte & 0xF0 == 0xA0:
                # Polyphonic key pressure
                data_bytes_length = 3
            elif byte & 0xF0 == 0xC0:
                # Program change
                data_bytes_length = 2
            else:
                raise ValueError(
                    f"Unknown Compensation of Alternative CC detected. data_bytes[0]={format(byte, "02X")}"
                )
        else:
            raise ValueError(
                f"Unknown Status byte detected. status_byte={format(status_byte, "02X")}"
            )

        data_bytes: bytes = stream.read(data_bytes_length)
        data_bytes_validate = data_bytes[1:] if status_byte == 0xFE else data_bytes
        if not is_data_bytes(data_bytes_validate):
            raise ValueError(
                f"Invalid Data Byte detected. data_bytes=`{data_bytes.hex(" ").upper()}`"
            )

        duration = None
        if status_type == 0x80 or status_type == 0x90:
            duration = read_variable_int(stream)

        return cls(status_byte, data_bytes, delta_time, duration)

    def write(self, stream: BufferedWriter) -> None:
        """Write

        Args:
            stream (BufferedReader): Output stream
        """
        write_extended_variable_int(stream, self.delta_time)
        stream.write(self.status_byte.to_bytes())
        stream.write(self.data_bytes)
        if self.duration is not None:
            write_variable_int(stream, self.duration)


@dataclass
class PTrackAbsoluteTimeEvent(MidiEvent):
    """P-Track Absolute Time Event"""

    port: int
    track: int
    time: int


@dataclass
class PTrackChunk(ChunkBase):
    """P-Track Chunk"""

    PORTS = 4
    CHANNELS_PER_PORT = 16
    TOTAL_CHANNELS = CHANNELS_PER_PORT * PORTS

    CHUNK_NUMBER_PORT_MAP = [0, 1, 2, 2, 3]

    events: list[PTrackEvent]

    @classmethod
    def from_generic(cls, generic: GenericChunk) -> Self:
        """From Generic Chunk

        Args:
            generic (GenericChunk): Generic Chunk

        Returns:
            Self: Instance of this class
        """
        stream = BytesIO(generic.payload)
        events: list[PTrackEvent] = []
        while True:
            message = PTrackEvent.read(stream)
            if message is None:
                # End of Track
                break
            events.append(message)
        return cls(generic.id, events)

    @staticmethod
    def __relocate_event(
        track_info_entry: PTrackInfoEntry | ExtendedPTrackInfoEntry,
        status_byte: int,
        data_bytes: bytes,
        time: int,
        group_channel: bool,
    ) -> list[PTrackAbsoluteTimeEvent]:
        status_type = status_byte & 0xF0

        if status_byte == 0xFE:
            # Compensation of Alternative CC
            status_byte = data_bytes[0]
            status_type = status_byte & 0xF0
            data_bytes = data_bytes[1:]

        relocated_events: list[PTrackAbsoluteTimeEvent] = []

        if status_type == 0xF0:
            # System messages
            for port in range(PTrackChunk.PORTS):
                if (track_info_entry.system_ex_ports >> port) & 0x0001 != 0x0001:
                    continue

                track = port * PTrackChunk.CHANNELS_PER_PORT
                relocated_events.append(
                    PTrackAbsoluteTimeEvent(
                        status_byte,
                        data_bytes,
                        port,
                        track,
                        time,
                    )
                )
            return relocated_events

        channel = status_byte & 0x0F
        channel_info_entry = track_info_entry.channel_info[channel]

        default_channel_group = track_info_entry.default_channel_groups[channel]
        # Fill default channel group
        if default_channel_group == 0x0000:
            default_channel_group = 0x0001 << channel

        for port in range(PTrackChunk.PORTS):
            if (channel_info_entry.ports >> port) & 0x0001 != 0x0001:
                continue

            for grouped_channel in range(PTrackChunk.CHANNELS_PER_PORT):
                if group_channel:
                    if (
                        track_info_entry.channel_groups[channel] >> grouped_channel
                    ) & 0x0001 != 0x0001:
                        continue
                else:
                    if (default_channel_group >> grouped_channel) & 0x0001 != 0x0001:
                        continue

                track = (port * PTrackChunk.CHANNELS_PER_PORT) + grouped_channel
                relocated_status_byte = status_type | grouped_channel
                relocated_events.append(
                    PTrackAbsoluteTimeEvent(
                        relocated_status_byte,
                        data_bytes,
                        port,
                        track,
                        time,
                    )
                )

        return relocated_events

    def track_number(self) -> int:
        """Track Number

        Returns:
            int: Track Number
        """
        return self.id[3]

    def exists_channel_message(self, channel: int) -> bool:
        """Check if there exists a message for a specific channel in the P-Track chunk

        Args:
            channel: Channel number

        Returns:
            bool: True if a message exists for the specified channel, False otherwise
        """
        return any(
            (event.status_byte & 0xF0) != 0xF0 and (event.status_byte & 0x0F) == channel
            for event in self.events
        )

    def _payload_buffer(self) -> bytes:
        stream = BytesIO()
        for message in self.events:
            message.write(stream)
        stream.seek(0)
        return stream.read()

    def to_json_serializable(self):
        json_events = []
        for message in self.events:
            json_events.append(
                {
                    "delta_time": message.delta_time,
                    "status_byte": format(message.status_byte, "02X"),
                    "data": message.data_bytes.hex(" ").upper(),
                    "duration": message.duration,
                }
            )
        return {"events": json_events}

    def absolute_time_track(
        self,
        track_info: PTrackInfoChunk | ExtendedPTrackInfoChunk | P3TrackInfoChunk,
    ) -> list[PTrackAbsoluteTimeEvent]:
        if isinstance(track_info, (PTrackInfoChunk, ExtendedPTrackInfoChunk)):
            track_info_list = track_info.data
        elif isinstance(track_info, P3TrackInfoChunk):
            track_info_list = [track_info]
        else:
            raise ValueError(
                "Argument `track_info` must be PTrackInfoChunk, ExtendedPTrackInfoChunk or P3TrackInfoChunk."
            )

        absolute_time_track: list[PTrackAbsoluteTimeEvent] = []
        track_info_entry = next(
            (
                entry
                for entry in track_info_list
                if entry.track_number == self.track_number()
            ),
            None,
        )
        if track_info_entry is None:
            raise ValueError(f"P-Track Info for track {self.track_number()} not found.")

        is_lossless_track = track_info_entry.is_lossless_track()

        absolute_time_track: list[PTrackAbsoluteTimeEvent] = []
        absolute_time = 0
        channel_grouping_enabled = False
        for event in self.events:
            absolute_time += event.delta_time

            status_type = event.status_byte_type()
            if status_type == 0x80:
                channel = event.channel()
                note_number = event.data_bytes[0]
                note_on_velocity = event.data_bytes[1]
                note_off_velocity = event.data_bytes[2]
                duration = event.duration
                if not is_lossless_track:
                    duration <<= 2
                # Note on
                absolute_time_track += PTrackChunk.__relocate_event(
                    track_info_entry,
                    0x90 | channel,
                    bytes([note_number, note_on_velocity]),
                    absolute_time,
                    channel_grouping_enabled,
                )
                # Note off
                absolute_time_track += PTrackChunk.__relocate_event(
                    track_info_entry,
                    0x80 | channel,
                    bytes([note_number, note_off_velocity]),
                    absolute_time + duration,
                    channel_grouping_enabled,
                )
            elif status_type == 0x90:
                channel = event.channel()
                note_number = event.data_bytes[0]
                note_on_velocity = event.data_bytes[1]
                duration = event.duration
                if not is_lossless_track:
                    duration <<= 2
                # Note on
                absolute_time_track += PTrackChunk.__relocate_event(
                    track_info_entry,
                    event.status_byte,
                    event.data_bytes,
                    absolute_time,
                    channel_grouping_enabled,
                )
                # Note off
                absolute_time_track += PTrackChunk.__relocate_event(
                    track_info_entry,
                    0x80 | channel,
                    bytes([note_number, 0x40]),
                    absolute_time + duration,
                    channel_grouping_enabled,
                )
            elif status_type == 0xA0:
                # CC: channel_info_entry.control_change_ax
                channel = event.channel()
                channel_info_entry = track_info_entry.channel_info[channel]
                absolute_time_track += PTrackChunk.__relocate_event(
                    track_info_entry,
                    0xB0 | channel,
                    bytes([channel_info_entry.control_change_ax, event.data_bytes[0]]),
                    absolute_time,
                    channel_grouping_enabled,
                )
            elif status_type == 0xC0:
                # CC: channel_info_entry.control_change_cx
                channel = event.channel()
                channel_info_entry = track_info_entry.channel_info[channel]
                absolute_time_track += PTrackChunk.__relocate_event(
                    track_info_entry,
                    0xB0 | channel,
                    bytes([channel_info_entry.control_change_cx, event.data_bytes[0]]),
                    absolute_time,
                    channel_grouping_enabled,
                )
            else:
                absolute_time_track += PTrackChunk.__relocate_event(
                    track_info_entry,
                    event.status_byte,
                    event.data_bytes,
                    absolute_time,
                    channel_grouping_enabled,
                )

            channel_grouping_enabled = event.status_byte == 0xFD

        absolute_time_track.sort(
            key=lambda absolute_time_event: absolute_time_event.time
        )

        return absolute_time_track
