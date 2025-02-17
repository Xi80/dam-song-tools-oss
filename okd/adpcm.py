from dataclasses import dataclass
from io import BufferedReader
import os
from typing import Self

FRAMES_PER_FRAME_GROUP = 18

SUB_FRAMES = 4
SUB_FRAME_NIBBLES = 28
SAMPLES_PER_FRAME = SUB_FRAME_NIBBLES * SUB_FRAMES

SHIFT_LIMIT = 12
INDEX_LIMIT = 3

K0 = [0.0, 0.9375, 1.796875, 1.53125]
K1 = [0.0, 0.0, -0.8125, -0.859375]
SIGNED_NIBBLES = [0, 1, 2, 3, 4, 5, 6, 7, -8, -7, -6, -5, -4, -3, -2, -1]


@dataclass
class AdpcmFrame:
    """ADPCM Frame"""

    parameters: bytes
    samples: bytes

    @classmethod
    def read(cls, stream: BufferedReader) -> Self:
        """Read

        Args:
            stream (BufferedReader): Input stream

        Returns:
            Self: Instance of this class
        """

        buffer = stream.read(128)
        if len(buffer) < 128:
            raise ValueError("Too less read bytes.")

        parameters = buffer[0:16]
        samples = buffer[16:128]

        return cls(parameters, samples)


class AdpcmDecoder:
    """ADPCM Decoder"""

    def __init__(self):
        """Constructor"""

        self.prev1 = 0
        self.prev2 = 0

    @staticmethod
    def __clamp16(value: float) -> int:
        """Clamp float to signed 16 bit int

        Args:
            value (float): float value

        Returns:
            int: int value
        """

        if value > 32767.0:
            return 32767
        elif value < -32768.0:
            return -32768
        else:
            return round(value)

    def __decode_sample(self, sp: int, su: int) -> int:
        """Decode Sample

        Args:
            sp (int): Parameter
            su (int): Sample

        Raises:
            ValueError: Parameter `shift` out of range.
            ValueError: Parameter `index` out of range.

        Returns:
            int: Decoded sample
        """

        shift = sp & 0x0F
        if SHIFT_LIMIT < shift:
            raise ValueError("Parameter `shift` out of range.")
        index = sp >> 4
        if INDEX_LIMIT < index:
            raise ValueError("Parameter `index` out of range.")

        sample = SIGNED_NIBBLES[su] << (12 - (shift & 0x1F))
        sample += K0[index] * self.prev1 + K1[index] * self.prev2
        sample = AdpcmDecoder.__clamp16(sample)

        self.prev2 = self.prev1
        self.prev1 = sample

        return sample

    def __decode_subframe(
        self, sp: bytes, samples: bytes, subframe_index: int, nibble: int
    ) -> list[int]:
        """Decode Subframe

        Args:
            sp (bytes): Parameter
            samples (bytes): Samples
            subframe_index (int): Subframe index
            nibble (int): Nibble (0: High, 1: Low)

        Returns:
            list[int]: Decoded subframe
        """

        decoded = [0] * SUB_FRAME_NIBBLES
        for i in range(SUB_FRAME_NIBBLES):
            su_index = i * SUB_FRAMES + subframe_index
            su = samples[su_index]
            su = su >> 4 if nibble != 0 else su & 0x0F
            decoded[i] = self.__decode_sample(sp, su)
        return decoded

    def __decode_frame(self, frame: AdpcmFrame) -> list[int]:
        """Decode Frame

        Args:
            frame (AdpcmFrame): Frame

        Returns:
            list[int]: Decoded Frame
        """

        decoded: list[float] = []
        for i in range(SUB_FRAMES):
            for j in range(2):
                sp_index = j + i * 2
                if 2 <= i:
                    sp_index += 4
                sp = frame.parameters[sp_index]
                decoded += self.__decode_subframe(sp, frame.samples, i, j)
        return decoded

    def __decode_frame_group(self, stream: BufferedReader) -> list[int]:
        """Decode Frame Group

        Args:
            stream (BufferedReader): Input stream

        Returns:
            list[int]: Decoded Frame Group
        """

        decoded: list[int] = []
        for _ in range(FRAMES_PER_FRAME_GROUP):
            frame = AdpcmFrame.read(stream)
            decoded += self.__decode_frame(frame)
        return decoded

    def decode(self, stream: BufferedReader) -> list[int]:
        """Decode

        Args:
            stream (BufferedReader): Input stream

        Returns:
            list[int]: Decoded samples
        """

        decoded: list[int] = []
        while True:
            try:
                decoded += self.__decode_frame_group(stream)
            except ValueError:
                break
            # Skip null bytes
            stream.seek(20, os.SEEK_CUR)
        return decoded
