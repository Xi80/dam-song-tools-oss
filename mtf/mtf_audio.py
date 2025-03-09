import numpy as np
import configparser
import io
from pydub import AudioSegment
from okd.adpcm import AdpcmDecoder

SETTING_FILE = "settings.ini"

class MtfAudio:
    """MTF Audio Processor Class"""

    def decode_adpcm(self, input_file):
        """Decodes ADPCM to AudioSegment"""
        with open(input_file, "rb") as f:
            data = f.read()

        stream = io.BytesIO(data)
        decoder = AdpcmDecoder()
        samples = decoder.decode(stream)
        samples = np.array(samples, dtype="int16")

        self.audio = AudioSegment(samples.tobytes(), frame_rate=22050, sample_width=2, channels=1)

    def decode_opus(self, input_file):
        """Loads OPUS(OGG), converts it to AudioSegment and adjust volume"""
        audio = AudioSegment.from_file(input_file)
        self.audio = audio + self.load_opus_volume_increase()  # Adjust volume from settings file

    def load_opus_volume_increase(self):
        """Loads Volume settings from ini"""
        config = configparser.ConfigParser()
        config.read(SETTING_FILE)
        return int(config.get("MtfAudio", "OpusVolumeIncrease", fallback=0))

    def apply_vol_events(self, vol_events, start_time):
        """Applies VolEvent"""
        self.audio = self.process_vol_events(vol_events, start_time, "Volume")
        self.audio = self.process_vol_events(vol_events, start_time, "Velocity")
        self.audio = self.process_vol_events(vol_events, start_time, "Pan")
        return self.audio

    def process_vol_events(self, vol_events, start_time, apply_type):
        """Processes audio VolEvent"""
        # Initial Values
        if apply_type == "Velocity":
            apply_value = 1.0
        elif apply_type == "Pan":
            apply_value = 0.0
        elif apply_type == "AdpcmVol":
            apply_value = 1.0

        # Applies VolEvents before start_time
        for event in sorted(vol_events, key=lambda e: e["clock"]):
            if event["clock"] > start_time:
                break
            if event["type"] == "Velocity" and apply_type == "Velocity":
                apply_value = event["value"] / 127.0
            elif event["type"] == "Pan" and apply_type == "Pan":
                apply_value = (event["value"] / 100.0) if -100 <= event["value"] <= 100 else 0
            elif event["type"] == "AdpcmVol" and apply_type == "AdpcmVol":
                apply_value = event["value"] / 127.0

        new_audio = self.audio

        # Audio at start_time
        if apply_type == "Velocity":
            new_audio = self.audio + (20 * np.log10(apply_value))  # Velocity
        elif apply_type == "Pan":
            new_audio = self.audio.pan(apply_value)
        elif apply_type == "AdpcmVol":
            new_audio = self.audio + (20 * np.log10(apply_value))  # Volume

        # Applies VolEvents after start_time
        for event in sorted(vol_events, key=lambda e: e["clock"]):
            if event["clock"] < start_time:
                continue

            event_time = event["clock"] - start_time

            if apply_type == "Velocity":
                if event["type"] != "Velocity":
                    continue
                apply_value = event["value"] / 127.0
            elif apply_type == "Pan":
                if event["type"] != "Pan":
                    continue
                apply_value = (event["value"] / 100.0) if -100 <= event["value"] <= 100 else 0
            elif apply_type == "AdpcmVol":
                if event["type"] != "AdpcmVol":
                    continue
                apply_value = event["value"] / 127.0

            segment = self.audio[event_time:]
            if apply_type == "Velocity":
                segment = segment + (20 * np.log10(apply_value))
            elif apply_type == "Pan":
                segment = segment.pan(apply_value)
            elif apply_type == "AdpcmVol":
                segment = segment + (20 * np.log10(apply_value))

            new_audio = new_audio[:event_time] + segment

        return new_audio