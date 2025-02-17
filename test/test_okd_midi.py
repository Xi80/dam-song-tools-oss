import bitstring
import unittest

from dam_okd_tools.okd_midi import (
    read_variable_int,
    write_variable_int,
    read_extended_variable_int,
    write_extended_variable_int,
)


class TestOkdMidi(unittest.TestCase):
    VALUES: list[tuple[int, bytes]] = [
        (0x000000, b"\x00"),
        (0x00003F, b"\x3f"),
        (0x00103F, b"\x7f\x3f"),
        (0x04103F, b"\x7f\x7f\x3f"),
    ]
    EXTENDED_VALUES: list[tuple[int, bytes]] = [
        (0x000000, b""),
        (0x00003F, b"\x3f"),
        (0x00103F, b"\x7f\x3f"),
        (0x04103F, b"\x7f\x7f\x3f"),
        (0x04107E, b"\x7f\x7f\x3f\x3f"),
        (0x04207E, b"\x7f\x7f\x3f\x7f\x3f"),
        (0x08207E, b"\x7f\x7f\x3f\x7f\x7f\x3f"),
    ]

    def test_read_varibale_int(self):
        for value, buffer in TestOkdMidi.VALUES:
            with self.subTest(value=value, buffer=buffer):
                stream = bitstring.BitStream(buffer)
                read_value = read_variable_int(stream)
                self.assertEqual(value, read_value)

        with self.assertRaises(ValueError):
            stream = bitstring.BitStream(b"\x7f\x7f\x7f")
            read_variable_int(stream)

    def test_write_variable_int(
        self,
    ):
        for value, buffer in TestOkdMidi.VALUES:
            with self.subTest(value=value, buffer=buffer):
                stream = bitstring.BitStream()
                write_variable_int(stream, value)
                self.assertEqual(buffer, stream.tobytes())

        with self.assertRaises(ValueError):
            stream = bitstring.BitStream()
            write_variable_int(stream, 0x04104F)

    def test_read_extended_variable_int(self):
        for value, buffer in TestOkdMidi.EXTENDED_VALUES:
            with self.subTest(value=value, buffer=buffer):
                stream = bitstring.BitStream(buffer + b"\x80")
                read_value = read_extended_variable_int(stream)
                self.assertEqual(value, read_value)

    def test_write_extended_variable_int(self):
        for value, buffer in TestOkdMidi.EXTENDED_VALUES:
            with self.subTest(value=value, buffer=buffer):
                stream = bitstring.BitStream()
                write_extended_variable_int(stream, value)
                self.assertEqual(buffer, stream.tobytes())


if __name__ == "__main__":
    unittest.main()
