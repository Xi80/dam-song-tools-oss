from logging import getLogger
import mido

from okd.okd_file import OkdGenericHeader, OkdFile
from okd.chunks import (
    MTrackInterpretation,
    MTrackChunk,
    PTrackInfoChunk,
    ExtendedPTrackInfoChunk,
    P3TrackInfoChunk,
    PTrackChunk,
    p_track_info_chunk_by_p_track_chunks,
    p3_track_info_chunk_by_p_track_chunks,
)
from okd.midi import get_meta_track, get_track_by_port_channel
from okd.m_track_conversion import midi_to_m_track
from okd.p_track_conversion import p_track_to_midi, midi_to_p_tracks, midi_to_p3_track

__logger = getLogger(__name__)


def okd_to_midi(okd: OkdFile, sysex_to_text: bool) -> mido.MidiFile:
    """Make MIDI file from OKD

    Args:
        okd (OkdFile): OKD file
        sysex_to_text (bool): Convert SysEx Messages to Text Meta Messages

    Raises:
        ValueError: Invalid input OKD.

    Returns:
        mido.MidiFile: MIDI file
    """

    __logger.info(f"OKD loaded. header={okd.header}")

    p_track_info: (
        PTrackInfoChunk | ExtendedPTrackInfoChunk | P3TrackInfoChunk | None
    ) = None
    p_tracks: list[PTrackChunk] = []

    for chunk in okd.chunks:
        chunk_id_hex = chunk.id.hex().upper()
        __logger.info(f"{type(chunk).__name__} found. id={chunk.id} (0x{chunk_id_hex})")
        if isinstance(chunk, MTrackChunk):
            m_track_interpritation = MTrackInterpretation.from_track(chunk)
        elif isinstance(chunk, PTrackInfoChunk):
            p_track_info = chunk
        elif isinstance(chunk, ExtendedPTrackInfoChunk):
            p_track_info = chunk
        elif isinstance(chunk, P3TrackInfoChunk):
            p_track_info = chunk
        elif isinstance(chunk, PTrackChunk):
            p_tracks.append(chunk)

    if m_track_interpritation is None or p_track_info is None or len(p_tracks) == 0:
        raise ValueError(
            "Invalid input OKD. Needed M-Track, P-Track Info and P-Tracks."
        )

    __logger.info("Make P-Track MIDI file.")
    return p_track_to_midi(
        m_track_interpritation, p_track_info, p_tracks, sysex_to_text
    )


def midi_to_okds(
    midi: mido.MidiFile, header: OkdGenericHeader
) -> tuple[OkdFile, OkdFile]:
    """MIDI to OKDs

    Args:
        midi (mido.MidiFile): MIDI file

    Raises:
        ValueError: Meta track not found.
        ValueError: P-Track not found.
        ValueError: P3-Track not found.

    Returns:
        tuple[OkdFile, OkdFile]: P-Track and P3-Track
    """

    meta_track = get_meta_track(midi.tracks)
    if meta_track is None:
        raise ValueError("Meta track not found.")

    m_track_chunk = midi_to_m_track(midi)

    p_track = [
        get_track_by_port_channel(midi.tracks, port, track)
        for port in range(2)
        for track in range(16)
    ]
    p_track = [track for track in p_track if track is not None]
    if len(p_track) < 1:
        raise ValueError("P-Track not found.")
    p_track_midi = mido.MidiFile()
    p_track_midi.tracks = [meta_track, *p_track]
    p_track_chunks = midi_to_p_tracks(p_track_midi)
    p_track_info_chunk = p_track_info_chunk_by_p_track_chunks(p_track_chunks)

    p3_track = get_track_by_port_channel(midi.tracks, 1, 8)
    if p3_track is None:
        raise ValueError("P3-Track not found.")
    for message in p3_track:
        if message.type == "midi_port":
            message.port = 2
        if hasattr(message, "channel"):
            message.channel = 14
    p3_track_midi = mido.MidiFile()
    p3_track_midi.tracks = [meta_track, p3_track]
    p3_track_chunk = midi_to_p3_track(p3_track_midi)
    p3_track_info_chunk = p3_track_info_chunk_by_p_track_chunks(p3_track_chunk)

    playing_okd = OkdFile(header, [m_track_chunk, p_track_info_chunk, *p_track_chunks])
    p3_okd = OkdFile(header, [p3_track_info_chunk, p3_track_chunk])
    return playing_okd, p3_okd
