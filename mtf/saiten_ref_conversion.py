from dataclasses import dataclass
from enum import Enum

import mido

from midi.time_converter import MidiTimeConverter
from midi.utils import (
    get_track_by_port_channel,
    get_first_and_last_note_times,
    get_time_signatures,
)


class SaitenRefEventType(Enum):
    OLD_HAMORUN_OFF_1 = 0x8B
    OLD_HAMORUN_ON_1 = 0x9B
    OLDHAMORUN_OFF_2 = 0x8C
    OLD_HAMORUN_ON_2 = 0x9C
    HAMORUN_OFF = 0x8D
    HAMORUN_ON = 0x9D
    NOTE_OFF = 0x8E
    NOTE_ON = 0x9E
    PLAY_MARK = 0xFF


class PlayMarkType(Enum):
    START_OF_SONG = 0x00
    END_OF_SONG = 0x01
    BEATMARK_ACCENT = 0x02
    BEATMARK_NOT_ACCENT = 0x03
    START_OF_VOCAL = 0x04
    START_OF_BRIDGE = 0x05
    START_OF_ENDING = 0x06
    START_OF_LYRICS_PAGE = 0x07
    START_OF_SABI = 0x08
    END_OF_SABI = 0x09
    START_OF_CLIMAX = 0x0A
    END_OF_CLIMAX = 0x0B
    SECOND_CHORUS_FADEOUT = 0x0C
    NOT_PLAY_MARK = 0x7F


@dataclass
class SaitenRefEvent:
    time: int
    event_type: SaitenRefEventType
    note_number: int
    value: int

    def to_dict(self):
        return {
            "Clock": self.time,
            "msg": [self.event_type.value, self.note_number, self.value],
        }


MIDI_M_TRACK_PORT = 16


def midi_to_saiten_ref(midi: mido.MidiFile) -> list[SaitenRefEvent]:
    absolute_time_track: list[SaitenRefEvent] = []

    midi_time_converter = MidiTimeConverter()
    midi_time_converter.load_from_midi(midi)

    melody_track = get_track_by_port_channel(midi.tracks, 1, 8)
    if melody_track is None:
        raise ValueError("Melody track not found.")

    melody_notes: list[tuple[int, int]] = []
    track_time = 0
    for midi_message in melody_track:
        track_time += midi_message.time
        absolute_time = midi_time_converter.ticks_to_ms(track_time)

        if not isinstance(midi_message, mido.Message):
            continue

        if midi_message.type == "note_on":  # type: ignore
            absolute_time_track.append(
                SaitenRefEvent(
                    absolute_time, SaitenRefEventType.NOTE_ON, midi_message.note, 100  # type: ignore
                )
            )
        elif midi_message.type == "note_off":  # type: ignore
            absolute_time_track.append(
                SaitenRefEvent(
                    absolute_time, SaitenRefEventType.NOTE_OFF, midi_message.note, 100  # type: ignore
                )
            )

        if midi_message.type == "note_on":  # type: ignore
            current_melody_note_start = absolute_time
            current_melody_node_number = midi_message.note  # type: ignore
        elif (
            midi_message.type == "note_off"  # type: ignore
            and midi_message.note == current_melody_node_number  # type: ignore
        ):
            melody_notes.append((current_melody_note_start, absolute_time))  # type: ignore

    if len(melody_notes) < 1:
        raise ValueError("Melody note not found.")

    m_track = get_track_by_port_channel(midi.tracks, MIDI_M_TRACK_PORT, 0)

    hooks: list[tuple[int, int]] = []

    two_chorus_fadeout_time = -1

    if m_track is not None:
        current_hook_start = -1
        track_time = 0
        for midi_message in midi.tracks[1]:
            track_time += midi_message.time
            absolute_time = midi_time_converter.ticks_to_ms(track_time)

            if not isinstance(midi_message, mido.Message):
                continue

            if midi_message.type == "note_on":  # type: ignore
                if midi_message.note == 48:  # type: ignore
                    current_hook_start = absolute_time
                elif midi_message.note == 72:  # type: ignore
                    two_chorus_fadeout_time = absolute_time
            elif midi_message.type == "note_off":  # type: ignore
                if midi_message.note == 48:  # type: ignore
                    hooks.append((current_hook_start, absolute_time))

    first_note_on_tick, last_note_off_tick = get_first_and_last_note_times(midi.tracks)
    first_note_on_time = midi_time_converter.ticks_to_ms(first_note_on_tick)
    last_note_off_time = midi_time_converter.ticks_to_ms(last_note_off_tick)

    time_signatures = get_time_signatures(midi.tracks)

    if len(time_signatures) > 0:
        current_beat_time = 0
        current_beat_count = time_signatures[0][1]
        while current_beat_time < last_note_off_time + 1:
            time_signature_time = current_beat_time
            time_signature = next(
                (
                    time_signature
                    for time_signature in reversed(time_signatures)
                    if time_signature[0] <= time_signature_time
                ),
                None,
            )
            if time_signature is None:
                raise ValueError("Time signature not found.")

            if current_beat_count < time_signature[1]:
                absolute_time_track.append(
                    SaitenRefEvent(
                        midi_time_converter.ticks_to_ms(current_beat_time),
                        SaitenRefEventType.PLAY_MARK,
                        0x30,
                        PlayMarkType.BEATMARK_NOT_ACCENT.value,
                    )
                )
                current_beat_count += 1
            else:
                absolute_time_track.append(
                    SaitenRefEvent(
                        midi_time_converter.ticks_to_ms(current_beat_time),
                        SaitenRefEventType.PLAY_MARK,
                        0x30,
                        PlayMarkType.BEATMARK_ACCENT.value,
                    )
                )
                current_beat_count = 1

            current_beat_time += midi.ticks_per_beat

    absolute_time_track.append(
        SaitenRefEvent(
            midi_time_converter.ticks_to_ms(first_note_on_time),
            SaitenRefEventType.PLAY_MARK,
            0x30,
            PlayMarkType.START_OF_SONG.value,
        )
    )
    absolute_time_track.append(
        SaitenRefEvent(
            midi_time_converter.ticks_to_ms(last_note_off_time),
            SaitenRefEventType.PLAY_MARK,
            0x30,
            PlayMarkType.END_OF_SONG.value,
        )
    )

    for hook_start, hook_end in hooks[:-1]:
        absolute_time_track.append(
            SaitenRefEvent(
                midi_time_converter.ticks_to_ms(hook_start),
                SaitenRefEventType.PLAY_MARK,
                0x30,
                PlayMarkType.START_OF_SABI.value,
            )
        )
        absolute_time_track.append(
            SaitenRefEvent(
                midi_time_converter.ticks_to_ms(hook_end),
                SaitenRefEventType.PLAY_MARK,
                0x30,
                PlayMarkType.END_OF_SABI.value,
            )
        )

    if len(hooks) > 0:
        last_hook_start, last_hook_end = hooks[-1]
        absolute_time_track.append(
            SaitenRefEvent(
                midi_time_converter.ticks_to_ms(last_hook_start),
                SaitenRefEventType.PLAY_MARK,
                0x30,
                PlayMarkType.START_OF_CLIMAX.value,
            )
        )
        absolute_time_track.append(
            SaitenRefEvent(
                midi_time_converter.ticks_to_ms(last_hook_end),
                SaitenRefEventType.PLAY_MARK,
                0x30,
                PlayMarkType.END_OF_CLIMAX.value,
            )
        )

    if two_chorus_fadeout_time != -1:
        absolute_time_track.append(
            SaitenRefEvent(
                midi_time_converter.ticks_to_ms(two_chorus_fadeout_time),
                SaitenRefEventType.PLAY_MARK,
                0x30,
                PlayMarkType.SECOND_CHORUS_FADEOUT.value,
            )
        )

    absolute_time_track.sort(key=lambda absolute_time_event: absolute_time_event.time)

    return absolute_time_track
