import math
import mido

from .chunks import MTrackEvent, MTrackAbsoluteTimeEvent, MTrackChunk
from midi.time_converter import MidiTimeConverter
from midi.utils import (
    get_track_by_port_channel,
    get_first_and_last_note_times,
    get_time_signatures,
)

MIDI_M_TRACK_PORT = 16


def __midi_to_absolute_time_track(midi: mido.MidiFile) -> list[MTrackAbsoluteTimeEvent]:
    midi_time_converter = MidiTimeConverter()
    midi_time_converter.load_from_midi(midi)

    melody_track = get_track_by_port_channel(midi.tracks, 1, 8)
    if melody_track is None:
        raise ValueError("Melody track not found.")

    melody_notes: list[tuple[int, int]] = []
    current_melody_note_start = -1
    current_melody_node_number = -1
    track_time = 0
    for midi_message in melody_track:
        track_time += midi_message.time
        absolute_time = midi_time_converter.ticks_to_ms(track_time)

        if not isinstance(midi_message, mido.Message):
            continue

        if midi_message.type == "note_on":  # type: ignore
            current_melody_note_start = absolute_time
            current_melody_node_number = midi_message.note  # type: ignore
        elif (
            midi_message.type == "note_off"  # type: ignore
            and midi_message.note == current_melody_node_number  # type: ignore
        ):
            melody_notes.append((current_melody_note_start, absolute_time))

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

    absolute_time_track: list[MTrackAbsoluteTimeEvent] = []

    time_signatures = get_time_signatures(midi.tracks)

    visible_guide_melody_delimiters: list[tuple[int, int]] = []
    for tick, numerator, denominator in time_signatures:
        absolute_time_track.append(
            MTrackAbsoluteTimeEvent(
                0xFF,
                bytes(bytearray([0x00, numerator, int(math.log2(denominator)), 0xFE])),
                midi_time_converter.ticks_to_ms(tick),
            )
        )

        melody_notes_copy = melody_notes.copy()
        current_page_start = -1
        while True:
            melody_note: tuple[int, int]
            try:
                melody_note = melody_notes_copy.pop(0)
            except IndexError:
                break
            melody_note_start, melody_note_end = melody_note

            if current_page_start == -1:
                current_page_start = melody_note_start
                visible_guide_melody_delimiters.append((melody_note_start, 0))
                continue

            next_melody_note: tuple[int, int]
            try:
                next_melody_note = melody_notes_copy[0]
            except IndexError:
                visible_guide_melody_delimiters.append((melody_note_end + 1, 2))
                break
            next_melody_note_start, next_melody_note_end = next_melody_note

            page_length = melody_note_end - current_page_start
            if 7000 < page_length:
                void_length = next_melody_note_start - melody_note_end
                if 7000 < void_length:
                    melody_notes_copy.pop(0)
                    visible_guide_melody_delimiters.append((melody_note_end + 1, 1))
                    current_page_start = -1
                else:
                    visible_guide_melody_delimiters.append((next_melody_note_start, 3))
                    current_page_start = next_melody_note_start

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
                    MTrackAbsoluteTimeEvent(
                        0xF2, b"", midi_time_converter.ticks_to_ms(current_beat_time)
                    )
                )
                current_beat_count += 1
            else:
                absolute_time_track.append(
                    MTrackAbsoluteTimeEvent(
                        0xF1, b"", midi_time_converter.ticks_to_ms(current_beat_time)
                    )
                )
                current_beat_count = 1

            current_beat_time += midi.ticks_per_beat

    absolute_time_track.append(
        MTrackAbsoluteTimeEvent(
            0xF6, b"\x00", midi_time_converter.ticks_to_ms(first_note_on_time)
        )
    )
    absolute_time_track.append(
        MTrackAbsoluteTimeEvent(
            0xF6, b"\x01", midi_time_converter.ticks_to_ms(last_note_off_time)
        )
    )

    for hook_start, hook_end in hooks[:-1]:
        absolute_time_track.append(
            MTrackAbsoluteTimeEvent(
                0xF3, b"\x00", midi_time_converter.ticks_to_ms(hook_start)
            )
        )
        absolute_time_track.append(
            MTrackAbsoluteTimeEvent(
                0xF3, b"\x01", midi_time_converter.ticks_to_ms(hook_end)
            )
        )

    if len(hooks) > 0:
        last_hook_start, last_hook_end = hooks[-1]
        absolute_time_track.append(
            MTrackAbsoluteTimeEvent(
                0xF3, b"\x02", midi_time_converter.ticks_to_ms(last_hook_start)
            )
        )
        absolute_time_track.append(
            MTrackAbsoluteTimeEvent(
                0xF3, b"\x03", midi_time_converter.ticks_to_ms(last_hook_end)
            )
        )

    for (
        visible_guide_melody_delimiter_time,
        visible_guide_melody_delimiter_type,
    ) in visible_guide_melody_delimiters:
        absolute_time_track.append(
            MTrackAbsoluteTimeEvent(
                0xF4,
                visible_guide_melody_delimiter_type.to_bytes(),
                midi_time_converter.ticks_to_ms(visible_guide_melody_delimiter_time),
            )
        )

    if two_chorus_fadeout_time != -1:
        absolute_time_track.append(
            MTrackAbsoluteTimeEvent(
                0xF5, b"", midi_time_converter.ticks_to_ms(two_chorus_fadeout_time)
            )
        )

    absolute_time_track.sort(key=lambda absolute_time_event: absolute_time_event.time)

    return absolute_time_track


def midi_to_m_track(
    midi: mido.MidiFile,
) -> MTrackChunk:
    absolute_time_track = __midi_to_absolute_time_track(midi)
    events: list[MTrackEvent] = []
    current_time = 0
    for event in absolute_time_track:
        delta_time = event.time - current_time
        events.append(MTrackEvent(event.status_byte, event.data_bytes, delta_time))
        current_time = event.time
    # End of Track
    events.append(MTrackEvent(0x00, b"\x00\x00\x00", 0))
    return MTrackChunk(b"\xffMR\x00", events)
