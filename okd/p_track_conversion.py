from dataclasses import dataclass, asdict
from logging import getLogger
import math
import mido

from .chunks import (
    MTrackInterpretation,
    PTrackInfoChunk,
    ExtendedPTrackInfoChunk,
    P3TrackInfoChunk,
    PTrackEvent,
    PTrackAbsoluteTimeEvent,
    PTrackChunk,
)
from midi.event import MidiEvent
from midi.time_converter import MidiTimeConverter
from midi.utils import get_track_port
from .mmt_tg import MultiPartEntry, MmtTg

__logger = getLogger(__name__)


@dataclass
class PTrackAbsoluteTimeMetaEvent(MidiEvent):
    """P-Track Absolute Time Meta Event"""

    track: int
    time: int


def __p_tracks_to_absolute_time_track(
    track_info: PTrackInfoChunk | ExtendedPTrackInfoChunk | P3TrackInfoChunk,
    tracks: list[PTrackChunk],
) -> list[PTrackAbsoluteTimeEvent]:
    absolute_time_track: list[PTrackAbsoluteTimeEvent] = []
    for track in tracks:
        absolute_time_track += track.absolute_time_track(track_info)

    absolute_time_track.sort(key=lambda absolute_time_event: absolute_time_event.time)
    return absolute_time_track


def p_track_to_midi(
    m_track_interpretation: MTrackInterpretation,
    track_info: PTrackInfoChunk | ExtendedPTrackInfoChunk | P3TrackInfoChunk,
    tracks: list[PTrackChunk],
    sysex_to_text: bool,
) -> mido.MidiFile:
    midi_time_converter = MidiTimeConverter()
    for time, tempo in m_track_interpretation.tempos:
        midi_time_converter.add_tempo_change(time, tempo)

    midi_device_1 = MmtTg()
    midi_device_2 = MmtTg()

    midi = mido.MidiFile()
    for port in range(PTrackChunk.PORTS):
        for channel in range(PTrackChunk.CHANNELS_PER_PORT):
            midi_track = mido.MidiTrack()

            # Set port
            midi_track.append(
                mido.MetaMessage(
                    "midi_port",
                    port=port,
                )
            )
            # Track setup messages
            midi_device = midi_device_1 if port < 2 else midi_device_2
            muti_part_entry_index = port // 2 * MmtTg.PARTS_PER_PORT + channel
            multi_part_entry = midi_device.multi_part_entry(muti_part_entry_index)
            part_number = port * MmtTg.PARTS_PER_PORT + channel
            track_setup_messages = MultiPartEntry.to_mido_messages(
                multi_part_entry,
                part_number % PTrackChunk.CHANNELS_PER_PORT,
                0,
            )
            midi_track += track_setup_messages

            midi.tracks.append(midi_track)

    absolute_time_track: list[PTrackAbsoluteTimeEvent | PTrackAbsoluteTimeMetaEvent] = (
        []
    )
    absolute_time_track += __p_tracks_to_absolute_time_track(track_info, tracks)
    if len(absolute_time_track) < 1:
        raise ValueError("Track empty.")

    for time, tempo in m_track_interpretation.tempos:
        absolute_time_track.append(
            PTrackAbsoluteTimeMetaEvent(
                0x51, b"\x03" + round(mido.bpm2tempo(tempo)).to_bytes(3, "big"), 0, time
            )
        )
    for time, numerator, denominator in m_track_interpretation.time_signatures:
        absolute_time_track.append(
            PTrackAbsoluteTimeMetaEvent(
                0x58,
                bytes([0x04, numerator, int(math.log2(denominator)), 24, 8]),
                0,
                time,
            ),
        )
    absolute_time_track.sort(key=lambda absolute_time_event: absolute_time_event.time)

    track_times = [0] * PTrackChunk.TOTAL_CHANNELS
    for event in absolute_time_track:
        status_type = event.status_byte & 0xF0

        tick = midi_time_converter.ms_to_ticks(event.time)

        delta_time = tick - track_times[event.track]
        track_times[event.track] = tick

        if isinstance(event, PTrackAbsoluteTimeMetaEvent):
            meta_message = mido.MetaMessage.from_bytes(
                b"\xff" + event.status_byte.to_bytes() + event.data_bytes
            )
            meta_message.time = delta_time
            midi.tracks[event.track].append(meta_message)
            continue

        if status_type == 0xF0:
            if event.status_byte != 0xF0:
                midi.tracks[event.track].append(
                    mido.MetaMessage(
                        type="text",
                        text=event.to_bytes().hex(" ").upper(),
                        time=delta_time,
                    )
                )
                continue

            # Convert SysEx event to General MIDI message
            midi_device = midi_device_1 if event.port < 2 else midi_device_2
            part_number = MmtTg.effecting_multi_part_number(event)
            if part_number is not None:
                before_sysex = midi_device.multi_part_entry(part_number)
                midi_device.receive_sysex_message(event)
                after_sysex = midi_device.multi_part_entry(part_number)
                multi_part_diff = dict(
                    asdict(after_sysex).items() - asdict(before_sysex).items()
                )
                track_number = event.port * MmtTg.PARTS_PER_PORT + part_number
                midi.tracks[track_number] += MultiPartEntry.to_mido_messages(
                    multi_part_diff,
                    part_number % PTrackChunk.CHANNELS_PER_PORT,
                    delta_time,
                )

            if sysex_to_text:
                midi.tracks[event.track].append(
                    mido.MetaMessage(
                        type="text",
                        text=event.to_bytes().hex(" ").upper(),
                        time=delta_time,
                    )
                )
                continue

        try:
            mido.messages.specs.SPEC_BY_STATUS[event.status_byte]
        except KeyError:
            __logger.warning(
                f"Unknown MIDI message detected. status_byte={hex(event.status_byte)}"
            )
            pass

        midi_message: mido.Message
        try:
            midi_message = mido.Message.from_bytes(event.to_bytes(), delta_time)
        except ValueError:
            __logger.warning(
                f"Invalid MIDI event data. message=`{event.to_bytes().hex(" ").upper()}`"
            )
            continue
        midi.tracks[event.track].append(midi_message)

    return midi


def __midi_to_absolute_time_tracks(
    midi: mido.MidiFile,
) -> list[list[PTrackAbsoluteTimeEvent]]:
    midi_time_converter = MidiTimeConverter()
    midi_time_converter.load_from_midi(midi)

    absolute_time_tracks: list[list[PTrackAbsoluteTimeEvent]] = [[]] * PTrackChunk.PORTS
    for i, midi_track in enumerate(midi.tracks):
        port = get_track_port(midi_track)
        if port is None:
            __logger.warning(f"Port undefined. track={i}")
            continue

        track_time = 0
        for midi_message in midi_track:
            midi_message_data = bytes(midi_message.bin())
            status_byte = midi_message_data[0]
            status_type = status_byte & 0xF0
            data_bytes = midi_message_data[1:]

            track_time += midi_message.time
            absolute_time = midi_time_converter.ticks_to_ms(track_time)

            if status_type == 0xF0:
                # System messages
                track = port * PTrackChunk.CHANNELS_PER_PORT
                absolute_time_tracks[port].append(
                    PTrackAbsoluteTimeEvent(
                        status_byte,
                        data_bytes,
                        port,
                        track,
                        absolute_time,
                    )
                )
            else:
                # Channel voice messages
                channel = status_byte & 0x0F
                track = (port * PTrackChunk.CHANNELS_PER_PORT) + channel
                absolute_time_tracks[port].append(
                    PTrackAbsoluteTimeEvent(
                        status_byte,
                        data_bytes,
                        port,
                        track,
                        absolute_time,
                    )
                )

    for absolute_time_track in absolute_time_tracks:
        absolute_time_track.sort(
            key=lambda absolute_time_event: absolute_time_event.time
        )

    return absolute_time_tracks


def __absolute_time_track_to_p_track(
    absolute_time_track: list[PTrackAbsoluteTimeEvent],
) -> list[PTrackEvent]:
    events: list[PTrackEvent] = []
    current_time = 0
    for event_index, event in enumerate(absolute_time_track):
        status_type = event.status_byte & 0xF0
        delta_time = event.time - current_time

        if status_type == 0x80:
            # Do nothing
            continue
        elif status_type == 0x90:
            channel = event.status_byte & 0x0F
            note_number = event.data_bytes[0]
            note_off_time = event.time
            for i in range(event_index, len(absolute_time_track)):
                note_off_event = absolute_time_track[i]
                note_off_event_status_type = note_off_event.status_byte & 0xF0
                note_off_event_channel = note_off_event.status_byte & 0x0F
                if (
                    note_off_event_status_type == 0x80
                    and note_off_event_channel == channel
                ):
                    note_off_event_note_number = note_off_event.data_bytes[0]
                    if note_off_event_note_number == note_number:
                        note_off_time = note_off_event.time
                        break
            duration = (note_off_time - event.time) >> 2
            events.append(
                PTrackEvent(
                    event.status_byte,
                    event.data_bytes,
                    delta_time,
                    duration,
                )
            )
        elif status_type == 0xA0 or status_type == 0xC0:
            data_bytes = event.status_byte.to_bytes() + event.data_bytes
            events.append(
                PTrackEvent(
                    0xFE,
                    data_bytes,
                    delta_time,
                )
            )
        elif status_type == 0xF0:
            if event.status_byte != 0xF0:
                continue

            events.append(
                PTrackEvent(
                    0xF0,
                    event.data_bytes,
                    delta_time,
                )
            )
        else:
            events.append(
                PTrackEvent(
                    event.status_byte,
                    event.data_bytes,
                    delta_time,
                )
            )

        current_time = event.time

    # End of Track
    events.append(PTrackEvent(0x00, b"\x00\x00\x00", 0))

    return events


def midi_to_p_tracks(midi: mido.MidiFile) -> list[PTrackChunk]:
    absolute_time_tracks = __midi_to_absolute_time_tracks(midi)
    p_tracks: list[PTrackChunk] = []
    track_count = 0
    for i in range(PTrackChunk.PORTS):
        if absolute_time_tracks[i] is None:
            continue

        track_number = track_count + 1 if track_count >= 2 else track_count
        p_tracks.append(
            PTrackChunk(
                b"\xffPR" + track_number.to_bytes(),
                __absolute_time_track_to_p_track(absolute_time_tracks[i]),
            )
        )
        track_count += 1
    return p_tracks


def midi_to_p3_track(midi: mido.MidiFile) -> PTrackChunk:
    absolute_time_tracks = __midi_to_absolute_time_tracks(midi)
    absolute_time_track = absolute_time_tracks[2]
    if absolute_time_tracks is None:
        raise ValueError("P-Track 2 not found.")
    absolute_time_track = [
        event
        for event in absolute_time_track
        # Note Off and Note On
        if event.status_byte_type() in [0x80, 0x90]
    ]
    return PTrackChunk(
        b"\xffPR\x02",
        __absolute_time_track_to_p_track(absolute_time_track),
    )
