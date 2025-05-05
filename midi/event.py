from dataclasses import dataclass
from io import BufferedWriter


@dataclass
class MidiEvent:
    """MIDI Event"""

    status_byte: int
    data_bytes: bytes

    def status_byte_type(self) -> int:
        """Get Status Byte type

        Returns:
            int: Status Byte type
        """
        return self.status_byte & 0xF0

    def channel(self) -> int:
        """Get channel

        Returns:
            int: Channel
        """
        return self.status_byte & 0x0F

    def write(self, stream: BufferedWriter) -> None:
        """Write

        Args:
            stream (BufferedReader): Output stream
        """
        stream.write(self.status_byte.to_bytes())
        stream.write(self.data_bytes)

    def to_bytes(self) -> bytes:
        """To bytes

        Returns:
            bytes: This instance as bytes
        """
        return self.status_byte.to_bytes() + self.data_bytes


@dataclass
class MidiTrackEvent(MidiEvent):
    """MIDI Track Event"""

    delta_time: int
