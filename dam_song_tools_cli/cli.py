import dataclasses
import fire
import logging
import mido
import numpy as np
import os
import json
import soundfile as sf
import tarfile
import shutil
import io
from typing import Any
from pydub import AudioSegment
from pathlib import Path

from okd import (
    YksOkdHeader,
    OkdFile,
    GenericChunk,
    MTrackInterpretation,
    MTrackChunk,
    PTrackInfoChunk,
    ExtendedPTrackInfoChunk,
    P3TrackInfoChunk,
    PTrackChunk,
    AdpcmChunk,
    okd_to_midi,
    midi_to_okds,
)

from mtf import MtfAudio

def default(item: Any):
    match item:
        case bytes():
            return item.hex(" ").upper()
        case _ if dataclasses.is_dataclass(item):
            return dataclasses.asdict(item)
        case _:
            raise TypeError(type(item))


class Cli:
    """DAM OKD Tools CLI

    Args:
        log_level (str, optional): Log level. Defaults to "INFO". {CRITICAL|FATAL|ERROR|WARN|WARNING|INFO|DEBUG|NOTSET}
    """

    @staticmethod
    def __config_logger(level: str) -> None:
        """Config logger

        Args:
            level (str): Log level
        """

        logging.basicConfig(
            level=level,
            format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        )

    def __init__(self, log_level="INFO"):
        """DAM OKD Tools CLI

        Args:
            log_level (str, optional): Log level. Defaults to "INFO". {CRITICAL|FATAL|ERROR|WARN|WARNING|INFO|DEBUG|NOTSET}
        """

        Cli.__config_logger(log_level)
        self.__logger = logging.getLogger(__name__)

    def dump_okd(self, okd_path, output_dir_path) -> None:
        """Dump chunks of a OKD

        Args:
            okd_path (str): Input OKD path
            output_dir_path (str): Output directory path

        Raises:
            ValueError: Argument `okd_path` must be str.
            ValueError: Argument `output_directory_path` must be str.
        """

        if not isinstance(okd_path, str):
            raise ValueError("Argument `okd_path` must be str.")
        if not isinstance(output_dir_path, str):
            raise ValueError("Argument `output_directory_path` must be str.")

        os.makedirs(output_dir_path, exist_ok=True)

        with open(okd_path, "rb") as okd_file:
            okd_file = OkdFile.read(okd_file)
            self.__logger.info(f"OKD loaded. header={okd_file.header}")

            for chunk in okd_file.chunks:
                chunk_id_hex = chunk.id.hex().upper()
                self.__logger.info(
                    f"{type(chunk).__name__} found. id={chunk.id} (0x{chunk_id_hex})"
                )
                if isinstance(chunk, GenericChunk):
                    output_path = os.path.join(
                        output_dir_path,
                        "chunk_0x" + chunk.id.hex().upper() + ".bin",
                    )
                    with open(output_path, "wb") as output_file:
                        output_file.write(chunk.id)
                        output_file.write(chunk.payload)
                elif isinstance(chunk, MTrackChunk):
                    m_track_interpritation = MTrackInterpretation.from_track(chunk)

                    track_number = chunk.id[3]
                    output_path = os.path.join(
                        output_dir_path, "m_track_" + str(track_number) + ".json"
                    )
                    output_json = json.dumps(
                        chunk.to_json_serializable(),
                        indent=2,
                    )
                    with open(output_path, "w") as output_file:
                        output_file.write(output_json)

                    output_path = os.path.join(
                        output_dir_path,
                        "m_track_interpretation_" + str(track_number) + ".json",
                    )
                    output_json = json.dumps(
                        m_track_interpritation,
                        indent=2,
                        default=default,
                    )
                    with open(output_path, "w") as output_file:
                        output_file.write(output_json)
                elif isinstance(chunk, PTrackInfoChunk):
                    output_path = os.path.join(output_dir_path, "p_track_info.json")
                    output_json = json.dumps(
                        chunk,
                        indent=2,
                        default=default,
                    )
                    with open(output_path, "w") as output_file:
                        output_file.write(output_json)
                elif isinstance(chunk, ExtendedPTrackInfoChunk):
                    output_path = os.path.join(
                        output_dir_path, "extended_p_track_info.json"
                    )
                    output_json = json.dumps(
                        chunk,
                        indent=2,
                        default=default,
                    )
                    with open(output_path, "w") as output_file:
                        output_file.write(output_json)
                elif isinstance(chunk, P3TrackInfoChunk):
                    output_path = os.path.join(output_dir_path, "p3_track_info.json")
                    output_json = json.dumps(
                        chunk,
                        indent=2,
                        default=default,
                    )
                    with open(output_path, "w") as output_file:
                        output_file.write(output_json)
                elif isinstance(chunk, PTrackChunk):
                    track_number = chunk.id[3]
                    output_path = os.path.join(
                        output_dir_path, "p_track_" + str(track_number) + ".json"
                    )
                    output_json = json.dumps(
                        chunk.to_json_serializable(),
                        indent=2,
                    )
                    with open(output_path, "w") as output_file:
                        output_file.write(output_json)
                elif isinstance(chunk, AdpcmChunk):
                    for i, track in enumerate(chunk.tracks):
                        output_path = os.path.join(output_dir_path, f"adpcm_{i}.wav")
                        samples = track.decode()
                        samples = np.array(samples, "int16")
                        sf.write(output_path, samples, 22050)
                else:
                    self.__logger.error("Unknown chunk type detected.")

    def pack_okd(self, okd_path, *chunk_paths, scramble=False):
        """Pack a OKD by directly inputting the required data in chunks

        Args:
            okd_path (str): Output OKD path
            chunk_paths (*str): Input chunk paths
            scramble (bool, optional): Scramble. Defaults to False.

        Raises:
            ValueError: Argument `okd_path` must be str.
            ValueError: Argument `chunk_paths` must be *str.
            ValueError: Argument `scramble` must be bool.
        """

        if not isinstance(okd_path, str):
            raise ValueError("Argument `output` must be str.")
        if not isinstance(scramble, bool):
            raise ValueError("Argument `scramble` must be bool.")

        for chunk_path in chunk_paths:
            if not isinstance(chunk_path, str):
                raise ValueError("Argument `input` must be *str.")

            chunks: list[GenericChunk] = []
            with open(chunk_path, "rb") as input_file:
                chunk = GenericChunk.read(input_file)
                chunk_id_hex = chunk.id.hex().upper()
                self.__logger.info(f"Add chunk {id} (0x{chunk_id_hex}).")
                chunks.append(chunk)

        header = YksOkdHeader(0, "YKS-1   v6.0v110", 0, 0, 0)
        self.__logger.info(f"Set header. header={header}")
        okd = OkdFile(header, chunks)
        with open(okd_path, "wb") as output_file:
            okd.write(output_file, scramble)

    def okd_to_midi(self, okd_path, midi_path, sysex_to_text=True) -> None:
        """Convert a OKD to a Standard MIDI File

        Args:
            okd_path (str): Input OKD path
            midi_path (str): Output MIDI path
            sysex_to_text (bool): Convert SysEx Messages to Text Meta Messages

        Raises:
            ValueError: Argument `okd_path` must be str.
            ValueError: Argument `midi_path` must be str.
        """

        if not isinstance(okd_path, str):
            raise ValueError("Argument `okd_path` must be str.")
        if not isinstance(midi_path, str):
            raise ValueError("Argument `midi_path` must be str.")
        if not isinstance(sysex_to_text, bool):
            raise ValueError("Argument `sysex_to_text` must be bool.")

        with open(okd_path, "rb") as okd_file:
            okd = OkdFile.read(okd_file)
            midi = okd_to_midi(okd, sysex_to_text)
            midi.save(midi_path)

    def midi_to_okd(
        self, midi_path: str, playing_okd_path: str, p3_okd_path: str, scramble=False
    ) -> None:
        """Convert a Standard MIDI File to a OKD

        Args:
            midi_path (str): Input MIDI file path
            playing_okd_path (str): Output Playing OKD path
            p3_okd_path (str): Output P3 OKD path
            scramble (bool, optional): Scramble. Defaults to False.

        Raises:
            ValueError: Argument `midi_path` must be str.
            ValueError: Argument `playing_okd_path` must be str.
            ValueError: Argument `p3_okd_path` must be str.
            ValueError: Argument `scramble` must be bool.
        """

        if not isinstance(midi_path, str):
            raise ValueError("Argument `midi_path` must be str.")
        if not isinstance(playing_okd_path, str):
            raise ValueError("Argument `playing_okd_path` must be str.")
        if not isinstance(p3_okd_path, str):
            raise ValueError("Argument `p3_okd_path` must be str.")
        if not isinstance(scramble, bool):
            raise ValueError("Argument `scramble` must be bool.")

        midi = mido.MidiFile(midi_path)
        header = YksOkdHeader(0, "YKS-1   v6.0v110", 0, 0, 0)
        self.__logger.info(f"Set header. header={header}")
        playing_okd, p3_okd = midi_to_okds(midi, header)
        with open(playing_okd_path, "wb") as playing_okd_file:
            self.__logger.info("Write Playing OKD.")
            playing_okd.write(playing_okd_file, scramble)
        with open(p3_okd_path, "wb") as p3_okd_file:
            self.__logger.info("Write P3 OKD.")
            p3_okd.write(p3_okd_file, scramble)
    
    def dump_mtf(self, audio_path: str, output_path: str, export_each_file: bool = False):
        """Mix MTF file into a single WAV file in extracted folder.
        
        Args:
            audio_path (str): Path to the MTF file
            output_path (str): Path to extract the archive into, output WAV will be saved inside
            export_each_file (bool): Whether to export each individual audio file (RawADPCM → .wav, OPUS → .ogg)
        """
        mixed_audio = AudioSegment.silent(duration=0)

        with open(audio_path, "rb") as f:
            data = bytearray(f.read())
        data[0:4] = b"\x1f\x8b\x08\x00" # GZipヘッダ

        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
            tar.extractall(path=output_path)
            members = tar.getmembers()
            root_folder_name = members[0].name.split('/')[0] if members else ''

        if not root_folder_name:
            print("Error: Failed to detect root folder in archive.")
            return

        extracted_root = os.path.join(output_path, root_folder_name) + '/mtf'

        json_files = [
            "PlayListChorus0.json",
            "PlayListGuideMelo0.json",
            "PlayListSynthChorus0.json",
            "PlayListDrum0.json",
            "PlayListUpper0.json",
        ]
        json_paths = [os.path.join(extracted_root, f) for f in json_files]

        for json_file in json_paths:
            if not os.path.exists(json_file):
                print(f"Warning: {json_file} not found, skipping.")
                continue

            with open(json_file, "r", encoding="utf-8") as f:
                playlist = json.load(f)

            vol_events = playlist.get("VolEvent", [])

            for item in playlist.get("AudioPlayListItem", []):
                file_name = item["file"]
                start_time = item["start_clk"] # ミリ秒
                input_path = os.path.join(extracted_root, file_name)

                mtf_audio_processor = MtfAudio()

                if item["codec"] == "RawADPCM":
                    if os.path.exists(input_path):
                        audio = mtf_audio_processor.decode_adpcm(input_path)
                        audio = mtf_audio_processor.apply_vol_events(vol_events, start_time)

                        if export_each_file:
                            adpcm_output_path = input_path + '.wav'
                            audio.export(adpcm_output_path, format='wav')
                    else:
                        print(f"Warning: {input_path} not found, skipping.")
                        continue
                elif item["codec"] == "OPUS":
                    if os.path.exists(input_path):
                        audio = mtf_audio_processor.decode_opus(input_path)
                        audio = mtf_audio_processor.apply_vol_events(vol_events, start_time)

                        if export_each_file:
                            ogg_output_path = input_path + '.ogg'
                            shutil.copy(input_path, ogg_output_path)
                    else:
                        print(f"Warning: {input_path} not found, skipping.")
                        continue
                else:
                    print(f"Warning: Unsupported codec {item['codec']}, skipping.")
                    continue

                # MIX
                if len(mixed_audio) < start_time + len(audio):
                    mixed_audio = mixed_audio.append(AudioSegment.silent(duration=start_time + len(audio) - len(mixed_audio)), crossfade=0)
                mixed_audio = mixed_audio.overlay(audio, position=int(start_time))

        # Export to a WAV file
        final_output_path = os.path.join(extracted_root, "output.wav")
        mixed_audio.export(final_output_path, format="wav")
        print(f"Mixed WAV file saved at: {final_output_path}")

def main() -> None:
    fire.Fire(Cli)


if __name__ == "__main__":
    main()
