from dataclasses import dataclass
from io import BufferedReader, BufferedWriter, BytesIO
import os
from typing import Self

from ..okd_midi import (
    read_status_byte,
    is_data_bytes,
    read_extended_variable_int,
    write_extended_variable_int,
)
from ..midi import MidiEvent, MidiTrackEvent

from . import ChunkBase
from . import GenericChunk


@dataclass
class MTrackEvent(MidiTrackEvent):
    """M-Track Event"""

    __END_OF_TRACK_MARK = b"\x00\x00\x00\x00"

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
                if byte != 0xFE:
                    raise ValueError(
                        f"Unterminated SysEx message detected. stop_byte={hex(byte)}"
                    )
                break
        return data_bytes

    @classmethod
    def read(cls, stream: BufferedReader) -> Self:
        """Read

        Args:
            stream (BufferedReader): Input stream

        Raises:
            ValueError: Unknown Status Byte detected

        Returns:
            Self: Instance of this class
        """

        delta_time = read_extended_variable_int(stream)

        end_of_track = stream.read(4)
        if end_of_track == MTrackEvent.__END_OF_TRACK_MARK:
            return None
        stream.seek(-4, os.SEEK_CUR)

        status_byte = read_status_byte(stream)

        # System messages
        if status_byte == 0xFF:
            # SysEx message
            data_bytes = MTrackEvent.read_sysex_data_bytes(stream)
            return cls(status_byte, data_bytes, delta_time)
        elif status_byte == 0xF1:
            # Strong beat
            data_bytes_length = 0
        elif status_byte == 0xF2:
            # Weak beat
            data_bytes_length = 0
        elif status_byte == 0xF3:
            # Hook section
            data_bytes_length = 1
        elif status_byte == 0xF4:
            # Visible Guide Melody page delimiter
            data_bytes_length = 1
        elif status_byte == 0xF5:
            # Two chorus fadeout position
            data_bytes_length = 0
        elif status_byte == 0xF6:
            # Playing section
            data_bytes_length = 1
        elif status_byte == 0xF8:
            # ADPCM playing section
            data_bytes_length = 1
        else:
            raise ValueError(
                f"Unknown Status Byte detected. status_byte={hex(status_byte)}"
            )

        data_bytes = stream.read(data_bytes_length)
        if not is_data_bytes(data_bytes):
            raise ValueError(
                f"Invalid Data Byte detected. data_bytes=`{data_bytes.hex(" ").upper()}`"
            )

        return cls(status_byte, data_bytes, delta_time)

    def write(self, stream: BufferedWriter) -> None:
        """Write

        Args:
            stream (BufferedReader): Output stream
        """

        write_extended_variable_int(stream, self.delta_time)
        stream.write(self.status_byte.to_bytes())
        stream.write(self.data_bytes)


@dataclass
class MTrackAbsoluteTimeEvent(MidiEvent):
    """M-Track Absolute Time Event"""

    time: int


@dataclass
class MTrackChunk(ChunkBase):
    """M-Track Chunk"""

    events: list[MTrackEvent]

    @classmethod
    def from_generic(cls, generic: GenericChunk) -> Self:
        """From Generic Chunk

        Args:
            generic (GenericChunk): Generic Chunk

        Returns:
            Self: Instance of this class
        """

        stream = BytesIO(generic.payload)
        events: list[MTrackEvent] = []
        while True:
            event = MTrackEvent.read(stream)
            if event is None:
                # End of Track
                break
            events.append(event)
        return cls(generic.id, events)

    def track_number(self) -> int:
        """Track Number

        Returns:
            int: Track Number
        """

        return self.id[3]

    def _payload_buffer(self) -> bytes:
        stream = BytesIO()
        for event in self.events:
            event.write(stream)
        stream.seek(0)
        return stream.read()

    def to_json_serializable(self):
        json_events = []
        for event in self.events:
            json_events.append(
                {
                    "delta_time": event.delta_time,
                    "status_byte": format(event.status_byte, "02X"),
                    "data": event.data_bytes.hex(" ").upper(),
                }
            )
        return {"events": json_events}

    def absolute_time_track(
        self,
    ) -> list[MTrackAbsoluteTimeEvent]:
        absolute_time_track: list[MTrackAbsoluteTimeEvent] = []
        absolute_time = 0
        for event in self.events:
            absolute_time += event.delta_time
            absolute_time_track.append(
                MTrackAbsoluteTimeEvent(
                    event.status_byte, event.data_bytes, absolute_time
                )
            )
        return absolute_time_track


@dataclass
class MTrackInterpretation:
    tempos: list[tuple[int, int]]
    time_signatures: list[tuple[int, int, int]]
    hooks: list[tuple[int, int]]
    visible_guide_melody_delimiters: list[tuple[int, int]]
    two_chorus_fadeout_time: int
    song_section: tuple[int, int]
    adpcm_sections: list[tuple[int, int]]

    @classmethod
    def from_track(cls, track: MTrackChunk):
        tempos: list[tuple[int, int]] = []
        time_signatures: list[tuple[int, int, int]] = []
        hooks: list[tuple[int, int]] = []
        visible_guide_melody_delimiters: list[tuple[int, int]] = []
        two_chorus_fadeout_time = -1
        song_section: tuple[int, int] = (-1, -1)
        adpcm_sections: list[tuple[int, int]] = []

        absolute_time_track = track.absolute_time_track()

        beats = 1
        current_beat_start = next(
            (
                event.time
                for event in absolute_time_track
                if event.status_byte == 0xF1 or event.status_byte == 0xF2
            ),
            -1,
        )
        current_bpm = 125
        current_hook_start_time = 0
        song_section_start = -1
        current_adpcm_section_start = -1

        for event in absolute_time_track:
            if event.status_byte == 0xF1:
                if current_beat_start != -1:
                    beat_length = event.time - current_beat_start
                    if beat_length == 0:
                        continue
                    bpm = round(60000 / beat_length)
                    if bpm != current_bpm:
                        tempos.append(
                            (
                                current_beat_start,
                                bpm,
                            )
                        )
                    current_bpm = bpm
                beats = 1
                current_beat_start = event.time
            elif event.status_byte == 0xF2:
                if current_beat_start != -1:
                    beat_length = event.time - current_beat_start
                    if beat_length == 0:
                        continue
                    bpm = round(60000 / beat_length)
                    if bpm != current_bpm:
                        tempos.append(
                            (
                                current_beat_start,
                                bpm,
                            )
                        )
                    current_bpm = bpm
                beats += 1
                current_beat_start = event.time
            elif event.status_byte == 0xF3:
                mark_type = event.data_bytes[0]
                if mark_type == 0x00 or mark_type == 0x02:
                    current_hook_start_time = event.time
                elif mark_type == 0x01 or mark_type == 0x03:
                    hooks.append((current_hook_start_time, event.time))
            elif event.status_byte == 0xF4:
                visible_guide_melody_delimiters.append(
                    (event.time, event.data_bytes[0])
                )
                pass
            elif event.status_byte == 0xF5:
                two_chorus_fadeout_time = event.time
            elif event.status_byte == 0xF6:
                mark_type = event.data_bytes[0]
                if mark_type == 0x00:
                    song_section_start = event.time
                elif mark_type == 0x01:
                    song_section = (song_section_start, event.time)
            elif event.status_byte == 0xF8:
                mark_type = event.data_bytes[0]
                if mark_type == 0x00:
                    current_adpcm_section_start = event.time
                elif mark_type == 0x01:
                    adpcm_sections.append((current_adpcm_section_start, event.time))
            elif event.status_byte == 0xFF:
                time_signatures.append(
                    (event.time, event.data_bytes[1], 2 ** event.data_bytes[2])
                )

        return cls(
            tempos,
            time_signatures,
            hooks,
            visible_guide_melody_delimiters,
            two_chorus_fadeout_time,
            song_section,
            adpcm_sections,
        )
