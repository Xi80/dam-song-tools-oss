from dataclasses import dataclass
from typing import Final, BinaryIO, Self

from fastcrc import crc16

# Magic bytes that identify SPRC files
_MAGIC_BYTES: Final[bytes] = b"SPRC"

# Header size in bytes
_HEADER_SIZE: Final[int] = 16


@dataclass
class SprcHeader:
    """
    SPRC Header class for handling SPRC file format headers.

    This class provides functionality to read, write, and validate SPRC headers,
    which include magic bytes, revision information, CRC checksums, and flags.

    Attributes:
        revision: Header revision number
        crc_value: CRC-16 checksum of the file content
        force_flag: Flag indicating if force processing is required
        unknown_0: Reserved bytes for future use
    """

    revision: int = 0
    crc_value: int = 0
    force_flag: int = 0
    unknown_0: bytes = b""

    @staticmethod
    def has_sprc_header(stream: BinaryIO) -> bool:
        """
        Check if a stream contains a valid SPRC header.

        This method reads the first 16 bytes of the stream to check for the SPRC
        magic bytes signature, then restores the stream position.

        Args:
            stream: Input stream to check

        Returns:
            True if the stream has a valid SPRC header, False otherwise
        """
        position = stream.tell()
        try:
            buffer = stream.read(_HEADER_SIZE)
            if len(buffer) < _HEADER_SIZE:
                return False

            magic_bytes = buffer[0:4]
            return magic_bytes == _MAGIC_BYTES
        finally:
            # Restore original stream position
            stream.seek(position)

    @classmethod
    def read(cls, stream: BinaryIO) -> Self:
        """
        Read SPRC header from a stream.

        Args:
            stream: Input stream to read from

        Returns:
            New SprcHeader instance

        Raises:
            ValueError: If the stream doesn't contain a valid SPRC header
        """
        buffer = stream.read(_HEADER_SIZE)
        if len(buffer) < _HEADER_SIZE:
            raise ValueError(
                f"Insufficient data: expected {_HEADER_SIZE} bytes, got {len(buffer)}"
            )

        # Check magic bytes
        magic_bytes = buffer[0:4]
        if magic_bytes != _MAGIC_BYTES:
            raise ValueError(
                f"Invalid magic bytes: expected {_MAGIC_BYTES!r}, got {magic_bytes!r}"
            )

        # Parse header fields
        revision = int.from_bytes(buffer[4:6], "big")
        crc_value = int.from_bytes(buffer[6:8], "big")
        force_flag = buffer[8]
        unknown_0 = buffer[9:16]

        return cls(revision, crc_value, force_flag, unknown_0)

    def validate_crc(self, data: bytes | BinaryIO) -> bool:
        """
        Validate data with stored CRC value.

        Args:
            data: Data bytes or stream to validate

        Returns:
            True if the calculated CRC matches the stored CRC, False otherwise
        """
        if isinstance(data, BinaryIO):
            # Save current position
            position = data.tell()

            try:
                # Skip SPRC header
                data.seek(_HEADER_SIZE)
                buffer = data.read()
                data_bytes = buffer
            finally:
                # Restore original position
                data.seek(position)
        else:
            data_bytes = data

        # Calculate CRC-16 (Genibus) of the data
        calculated_crc = crc16.genibus(data_bytes)

        return calculated_crc == self.crc_value

    def write(self, stream: BinaryIO) -> None:
        """
        Write SPRC header to a stream.

        Args:
            stream: Output stream to write to
        """
        # Write magic bytes
        stream.write(_MAGIC_BYTES)

        # Write header fields
        stream.write(self.revision.to_bytes(2, "big"))
        stream.write(self.crc_value.to_bytes(2, "big"))
        stream.write(self.force_flag.to_bytes(1, "big"))
        stream.write(self.unknown_0)

    @classmethod
    def create(cls, data: bytes, revision: int = 1, force_flag: int = 0) -> Self:
        """
        Create a new SPRC header for the given data.

        Args:
            data: Data bytes to calculate CRC for
            revision: Header revision number (default: 1)
            force_flag: Force processing flag (default: 0)

        Returns:
            New SprcHeader instance with calculated CRC
        """
        # Calculate CRC-16 (Genibus) of the data
        crc_value = crc16.genibus(data)

        # Create unknown_0 bytes (all zeros)
        unknown_0 = bytes(7)

        return cls(revision, crc_value, force_flag, unknown_0)
