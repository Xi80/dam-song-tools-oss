import mido


def is_meta_track(track: mido.MidiTrack) -> bool:
    """Check if a MIDI track contains any meta messages.

    Args:
        track (mido.MidiTrack): MIDI track to check

    Returns:
        bool: True if track contains at least one meta message, False otherwise
    """
    return any(isinstance(message, mido.MetaMessage) for message in track)


def get_meta_track(tracks: list[mido.MidiTrack]) -> mido.MidiTrack | None:
    """Find and return the first meta track from a list of MIDI tracks.

    Args:
        tracks: List of MIDI tracks to search through.

    Returns:
        mido.MidiTrack | None: The first meta track found, or None if no meta track exists.
    """
    return next(
        (track for track in tracks if is_meta_track(track)),
        None,
    )


def get_track_port(track: mido.MidiTrack) -> int | None:
    """Retrieves the MIDI port number from a MIDI track.

    Args:
        track (mido.MidiTrack): A MIDI track object to extract port information from.

    Returns:
        int | None: The port number if a midi_port message exists, None otherwise.
    """
    return next(
        (message.port for message in track if message.type == "midi_port"), None
    )


def get_track_by_port_channel(
    tracks: list[mido.MidiTrack], port: int, channel: int
) -> mido.MidiTrack | None:
    """Find the first MIDI track that matches the specified port and channel numbers.

    Args:
        tracks (list[mido.MidiTrack]): List of MIDI tracks to search through
        port (int): Target MIDI port number
        channel (int): Target MIDI channel number

    Returns:
        mido.MidiTrack | None: The first matching MIDI track, or None if no match is found
    """
    for track in tracks:
        has_matching_port = False
        has_matching_channel = False

        has_matching_port = any(
            message.type == "midi_port" and message.port == port for message in track
        )

        if has_matching_port:
            has_matching_channel = any(
                message.type == "note_on" and message.channel == channel
                for message in track
            )

            if has_matching_channel:
                return track


def get_first_and_last_note_times(tracks: list[mido.MidiTrack]):
    """Get the absolute time of the first and last notes in a MIDI tracks

    Args:
        tracks (list[mido.MidiTrack]): MIDI tracks

    Returns:
        tuple: (first_note_time, last_note_time) in seconds. Returns (None, None) if no notes are found
    """
    first_note_time = 0xFFFFFFFF
    last_note_time = 0
    for track in tracks:
        absolute_time = 0
        for message in track:
            absolute_time += message.time

            if message.type == "note_on":
                if absolute_time < first_note_time:
                    first_note_time = absolute_time
            if message.type == "note_off":
                if absolute_time > last_note_time:
                    last_note_time = absolute_time

    return first_note_time, last_note_time


def get_time_signatures(tracks: list[mido.MidiTrack]) -> list[tuple[int, int, int]]:
    """Get time signatures from MIDI tracks

    Args:
        tracks: MIDI tracks

    Returns:
        list[tuple[int, int, int]]: List of (tick, numerator, denominator)
    """
    time_signatures: list[tuple[int, int, int]] = []
    for track in tracks:
        absolute_tick = 0
        for message in track:
            absolute_tick += message.time
            if message.type == "time_signature":
                time_signatures.append(
                    (absolute_tick, message.numerator, message.denominator)
                )
    return sorted(time_signatures, key=lambda x: x[0])
