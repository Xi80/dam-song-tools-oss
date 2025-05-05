from logging import getLogger

from midi.event import MidiEvent

from .midi_parameter_change_table import System, MultiPartEntry


class MmtTg:
    """YAMAHA MMT TG MIDI Device"""

    PARTS_PER_PORT = 16
    PORTS = 2
    PARTS = PARTS_PER_PORT * PORTS

    sound_module_mode: int
    native_parameter_memory: list[int]

    @staticmethod
    def __is_sysex_message(event: MidiEvent) -> bool:
        if len(event.data_bytes) < 2:
            return False
        if event.status_byte != 0xF0:
            return False
        end_mark = event.data_bytes[-1]
        if end_mark != 0xF7:
            return False
        return True

    @staticmethod
    def __is_universal_realtime_message(event: MidiEvent) -> bool:
        if not MmtTg.__is_sysex_message(event):
            return False
        if len(event.data_bytes) < 7:
            return False
        manufacture_id = event.data_bytes[0]
        if manufacture_id != 0x7F:
            return False
        return True

    @staticmethod
    def __is_universal_non_realtime_message(event: MidiEvent) -> bool:
        if not MmtTg.__is_sysex_message(event):
            return False
        if len(event.data_bytes) < 5:
            return False
        manufacture_id = event.data_bytes[0]
        if manufacture_id != 0x7E:
            return False
        return True

    @staticmethod
    def __is_native_parameter_change_message(event: MidiEvent) -> bool:
        if not MmtTg.__is_sysex_message(event):
            return False
        if len(event.data_bytes) < 9:
            return False
        manufacture_id = event.data_bytes[0]
        if manufacture_id != 0x43:
            return False
        return True

    @staticmethod
    def effecting_multi_part_number(event: MidiEvent):
        if not MmtTg.__is_native_parameter_change_message(event):
            return
        if event.data_bytes[3] != 0x02:
            return
        return MultiPartEntry.ENTRY_INDEX_TO_PART_NUMBER_TABLE[event.data_bytes[4]]

    def __init__(self) -> None:
        self.__logger = getLogger(__name__)

        self.initialize_state()

    def initialize_state(self) -> None:
        self.sound_module_mode = 0x00
        self.native_parameter_memory = [0x00] * 0x200000

        # Set default value
        for entry_index in range(0x20):
            entry_address = 0x008000 + (entry_index << 7)

            self.native_parameter_memory[entry_address + 0x01] = 0x00
            self.native_parameter_memory[entry_address + 0x02] = 0x00
            self.native_parameter_memory[entry_address + 0x03] = 0x00
            self.native_parameter_memory[entry_address + 0x04] = entry_index
            self.native_parameter_memory[entry_address + 0x05] = 0x01
            self.native_parameter_memory[entry_address + 0x06] = 0x01
            self.native_parameter_memory[entry_address + 0x07] = 0x01
            self.native_parameter_memory[entry_address + 0x08] = 0x01
            self.native_parameter_memory[entry_address + 0x09] = 0x01
            self.native_parameter_memory[entry_address + 0x0A] = 0x01
            self.native_parameter_memory[entry_address + 0x0B] = 0x01
            self.native_parameter_memory[entry_address + 0x0C] = 0x01
            self.native_parameter_memory[entry_address + 0x0D] = 0x01
            self.native_parameter_memory[entry_address + 0x0E] = 0x01
            self.native_parameter_memory[entry_address + 0x0F] = 0x01
            self.native_parameter_memory[entry_address + 0x10] = 0x01
            self.native_parameter_memory[entry_address + 0x11] = 0x01
            self.native_parameter_memory[entry_address + 0x12] = 0x01
            self.native_parameter_memory[entry_address + 0x13] = 0x01
            self.native_parameter_memory[entry_address + 0x14] = 0x01

            self.native_parameter_memory[entry_address + 0x15] = 0x01
            self.native_parameter_memory[entry_address + 0x16] = 0x01
            self.native_parameter_memory[entry_address + 0x17] = 0x01
            self.native_parameter_memory[entry_address + 0x18] = 0x01
            self.native_parameter_memory[entry_address + 0x19] = 0x08
            self.native_parameter_memory[entry_address + 0x1A] = 0x00
            self.native_parameter_memory[entry_address + 0x1B] = 0x64
            self.native_parameter_memory[entry_address + 0x1C] = 0x40
            self.native_parameter_memory[entry_address + 0x1D] = 0x40
            self.native_parameter_memory[entry_address + 0x1E] = 0x40
            self.native_parameter_memory[entry_address + 0x1F] = 0x00
            self.native_parameter_memory[entry_address + 0x20] = 0x7F
            self.native_parameter_memory[entry_address + 0x21] = 0x10
            self.native_parameter_memory[entry_address + 0x22] = 0x11
            self.native_parameter_memory[entry_address + 0x23] = 0x7F
            self.native_parameter_memory[entry_address + 0x24] = 0x00
            self.native_parameter_memory[entry_address + 0x25] = 0x40
            self.native_parameter_memory[entry_address + 0x26] = 0x00

            self.native_parameter_memory[entry_address + 0x27] = 0x40
            self.native_parameter_memory[entry_address + 0x28] = 0x40
            self.native_parameter_memory[entry_address + 0x29] = 0x40
            self.native_parameter_memory[entry_address + 0x2A] = 0x40
            self.native_parameter_memory[entry_address + 0x2B] = 0x40
            self.native_parameter_memory[entry_address + 0x2C] = 0x40
            self.native_parameter_memory[entry_address + 0x2D] = 0x40
            self.native_parameter_memory[entry_address + 0x2E] = 0x40

            self.native_parameter_memory[entry_address + 0x2F] = 0x40
            self.native_parameter_memory[entry_address + 0x30] = 0x40
            self.native_parameter_memory[entry_address + 0x31] = 0x40
            self.native_parameter_memory[entry_address + 0x32] = 0x40
            self.native_parameter_memory[entry_address + 0x33] = 0x40
            self.native_parameter_memory[entry_address + 0x34] = 0x40
            self.native_parameter_memory[entry_address + 0x35] = 0x40
            self.native_parameter_memory[entry_address + 0x36] = 0x40
            self.native_parameter_memory[entry_address + 0x37] = 0x40
            self.native_parameter_memory[entry_address + 0x38] = 0x40
            self.native_parameter_memory[entry_address + 0x39] = 0x40
            self.native_parameter_memory[entry_address + 0x3A] = 0x40

            self.native_parameter_memory[entry_address + 0x3B] = 0x40
            self.native_parameter_memory[entry_address + 0x3C] = 0x40
            self.native_parameter_memory[entry_address + 0x3D] = 0x40
            self.native_parameter_memory[entry_address + 0x3E] = 0x0A
            self.native_parameter_memory[entry_address + 0x3F] = 0x00

            self.native_parameter_memory[entry_address + 0x41] = 0x42
            self.native_parameter_memory[entry_address + 0x42] = 0x40
            self.native_parameter_memory[entry_address + 0x43] = 0x40
            self.native_parameter_memory[entry_address + 0x44] = 0x00
            self.native_parameter_memory[entry_address + 0x45] = 0x00

            self.native_parameter_memory[entry_address + 0x47] = 0x40
            self.native_parameter_memory[entry_address + 0x48] = 0x40
            self.native_parameter_memory[entry_address + 0x49] = 0x40
            self.native_parameter_memory[entry_address + 0x4A] = 0x00
            self.native_parameter_memory[entry_address + 0x4B] = 0x00

            self.native_parameter_memory[entry_address + 0x4D] = 0x40
            self.native_parameter_memory[entry_address + 0x4E] = 0x40
            self.native_parameter_memory[entry_address + 0x4F] = 0x40
            self.native_parameter_memory[entry_address + 0x50] = 0x00
            self.native_parameter_memory[entry_address + 0x51] = 0x00

            self.native_parameter_memory[entry_address + 0x53] = 0x40
            self.native_parameter_memory[entry_address + 0x54] = 0x40
            self.native_parameter_memory[entry_address + 0x55] = 0x40
            self.native_parameter_memory[entry_address + 0x56] = 0x00
            self.native_parameter_memory[entry_address + 0x57] = 0x00

            self.native_parameter_memory[entry_address + 0x59] = 0x40
            self.native_parameter_memory[entry_address + 0x5A] = 0x40
            self.native_parameter_memory[entry_address + 0x5B] = 0x40
            self.native_parameter_memory[entry_address + 0x5C] = 0x00
            self.native_parameter_memory[entry_address + 0x5D] = 0x00

            self.native_parameter_memory[entry_address + 0x5F] = 0x00
            self.native_parameter_memory[entry_address + 0x60] = 0x00

    def __receive_universal_realtime_message(self, event: MidiEvent) -> None:
        if event.status_byte != 0xF0:
            raise ValueError(
                f"Invalid status_byte. status_byte={hex(event.status_byte)}"
            )
        manufacture_id = event.data_bytes[0]
        if manufacture_id != 0x7F:
            raise ValueError(
                f"Invalid manufacture_id. manufacture_id={hex(manufacture_id)}"
            )
        target_device_id = event.data_bytes[1]
        sub_id_1 = event.data_bytes[2]
        if sub_id_1 != 0x04:
            self.__logger.warning(
                f"Unknown sub_id_1 detected. sub_id_1={hex(sub_id_1)}"
            )

        sub_id_2 = event.data_bytes[3]
        if sub_id_2 == 0x01:
            # Master Volume
            volume_lsb = event.data_bytes[4]
            volume_msb = event.data_bytes[5]
            # MASTER VOLUME
            self.native_parameter_memory[0x000004] = volume_msb
        elif sub_id_2 == 0x02:
            # Master Balance
            balance_lsb = event.data_bytes[4]
            balance_msb = event.data_bytes[5]
            # MASTER PAN
            self.native_parameter_memory[0x000006] = balance_msb
        else:
            self.__logger.warning(
                f"Unknown sub_id_2 detected. sub_id_2={hex(sub_id_2)}"
            )

    def __receive_universal_non_realtime_message(self, event: MidiEvent) -> None:
        if event.status_byte != 0xF0:
            raise ValueError(
                f"Invalid status_byte. status_byte={hex(event.status_byte)}"
            )
        manufacture_id = event.data_bytes[0]
        if manufacture_id != 0x7E:
            raise ValueError(
                f"Invalid manufacture_id. manufacture_id={hex(manufacture_id)}"
            )
        target_device_id = event.data_bytes[1]
        sub_id_1 = event.data_bytes[2]
        if sub_id_1 != 0x09:
            self.__logger.warning(
                f"Unknown sub_id_1 detected. sub_id_1={hex(sub_id_1)}"
            )

        sub_id_2 = event.data_bytes[3]
        if sub_id_2 == 0x01:
            self.sound_module_mode = event.data_bytes[4]
        else:
            self.__logger.warning(
                f"Unknown sub_id_2 detected. sub_id_2={hex(sub_id_2)}"
            )

    def __receive_native_parameter_change_message(self, event: MidiEvent) -> None:
        if event.status_byte != 0xF0:
            raise ValueError(
                f"Invalid status_byte. status_byte={hex(event.status_byte)}"
            )
        manufacture_id = event.data_bytes[0]
        if manufacture_id != 0x43:
            raise ValueError(
                f"Invalid manufacture_id. manufacture_id={hex(manufacture_id)}"
            )
        device_number_byte = event.data_bytes[1]
        if device_number_byte & 0xF0 != 0x10:
            raise ValueError(
                f"Invalid device_number_byte detected. device_number_byte={hex(device_number_byte)}"
            )
        device_number = device_number_byte & 0x0F
        model_id = event.data_bytes[2]

        address = (
            event.data_bytes[3] << 14 | event.data_bytes[4] << 7 | event.data_bytes[5]
        )
        data_length = len(event.data_bytes) - 8
        data = event.data_bytes[6 : 6 + data_length]
        check_sum = event.data_bytes[-2]

        if address == 0x00007F:
            # All Parameters Reset
            self.initialize_state()
            return
        self.native_parameter_memory[address : address + data_length] = data

    def receive_sysex_message(self, event: MidiEvent) -> None:
        if len(event.data_bytes) < 1:
            raise ValueError("Invalid event.data legnth.")

        if event.status_byte != 0xF0:
            raise ValueError(
                f"Invalid status_byte. status_byte={hex(event.status_byte)}"
            )
        end_mark = event.data_bytes[-1]
        if end_mark != 0xF7:
            raise ValueError(f"Invalid end_mark. end_mark={hex(end_mark)}")

        manufacture_id = event.data_bytes[0]
        if manufacture_id == 0x7F:
            self.__receive_universal_realtime_message(event)
        elif manufacture_id == 0x7E:
            self.__receive_universal_non_realtime_message(event)
        elif manufacture_id == 0x43:
            return self.__receive_native_parameter_change_message(event)
        else:
            self.__logger.warning(
                f"Unknown manufacture_id detected. manufacture_id={hex(manufacture_id)}"
            )

    def system(self) -> System:
        return System.from_memory(self.native_parameter_memory)

    def multi_part_entry(self, part_number: int) -> MultiPartEntry:
        return MultiPartEntry.from_memory(self.native_parameter_memory, part_number)

    def multi_part_entries(self) -> list[MultiPartEntry]:
        return [
            self.multi_part_entry(part_number) for part_number in range(MmtTg.PARTS)
        ]
