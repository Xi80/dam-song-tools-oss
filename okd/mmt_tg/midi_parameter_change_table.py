from dataclasses import dataclass, asdict
import mido
from typing import Union


@dataclass
class System:
    master_tune: int
    master_volume: int
    transpose: int
    master_pan: int
    master_cutoff: int
    master_pitch_modulation_depth: int
    variation_effect_send_control_change_number: int

    @classmethod
    def from_memory(cls, memory: list[int]):
        master_tune = (
            ((memory[0x000000] & 0x0F) << 12)
            | ((memory[0x000001] & 0x0F) << 8)
            | ((memory[0x000002] & 0x0F) << 4)
            | (memory[0x000003] & 0x0F)
        )
        master_volume = memory[0x000004]
        transpose = memory[0x000005]
        master_pan = memory[0x000006]
        master_cutoff = memory[0x000007]
        master_pitch_modulation_depth = memory[0x000008]
        variation_effect_send_control_change_number = memory[0x000009]

        return cls(
            master_tune,
            master_volume,
            transpose,
            master_pan,
            master_cutoff,
            master_pitch_modulation_depth,
            variation_effect_send_control_change_number,
        )


@dataclass
class MultiEffect:
    chorus_type: int
    variation_type: int
    pre_variation_type: int
    pre_reverb_type: int
    reverb_input: int
    chorus_input: int
    variation_input: int
    dry_level: int
    reverb_return: int
    chorus_return: int
    variation_return: int
    send_variation_to_chorus: int
    send_variation_to_reverb: int
    send_chorus_to_reverb: int

    chorus_param_1: int
    chorus_param_2: int
    chorus_param_3: int
    chorus_param_4: int
    chorus_param_5: int
    chorus_param_6: int
    chorus_param_7: int
    chorus_param_8: int
    chorus_param_9: int
    chorus_param_10: int

    variation_param_1_msb: int
    variation_param_1_lsb: int
    variation_param_2_msb: int
    variation_param_2_lsb: int
    variation_param_3_msb: int
    variation_param_3_lsb: int
    variation_param_4_msb: int
    variation_param_4_lsb: int
    variation_param_5_msb: int
    variation_param_5_lsb: int
    variation_param_6: int
    variation_param_7: int
    variation_param_8: int
    variation_param_9: int
    variation_param_10: int

    pre_variation_param_1: int
    pre_variation_param_2: int
    pre_variation_param_3: int
    pre_variation_param_4: int
    pre_variation_param_5: int
    pre_variation_param_6: int
    pre_variation_param_7: int
    pre_variation_param_8: int

    pre_reverb_param_1: int
    pre_reverb_param_2: int
    pre_reverb_param_3: int
    pre_reverb_param_4: int
    pre_reverb_param_5: int
    pre_reverb_param_6: int
    pre_reverb_param_7: int
    pre_reverb_param_8: int
    pre_reverb_param_9: int

    reverb_param_1: int
    reverb_param_2: int
    reverb_param_3: int
    reverb_param_4: int
    reverb_param_5: int
    reverb_param_6: int
    reverb_param_7: int
    reverb_param_8: int
    reverb_param_9: int
    reverb_param_10: int


@dataclass
class MultiPartEntry:
    PART_NUMBER_TO_ENTRY_INDEX_TABLE = [
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x00,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
        0x0F,
        0x11,
        0x12,
        0x13,
        0x14,
        0x15,
        0x16,
        0x17,
        0x18,
        0x19,
        0x10,
        0x1A,
        0x1B,
        0x1C,
        0x1D,
        0x1E,
        0x1F,
    ]

    ENTRY_INDEX_TO_PART_NUMBER_TABLE = [
        0x09,
        0x00,
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
        0x0F,
        0x19,
        0x10,
        0x11,
        0x12,
        0x13,
        0x14,
        0x15,
        0x16,
        0x17,
        0x18,
        0x1A,
        0x1B,
        0x1C,
        0x1D,
        0x1E,
        0x1F,
    ]

    bank_select_msb: int
    bank_select_lsb: int
    program_number: int
    rcv_channel: int
    rcv_pitch_bend: int
    rcv_ch_after_touch: int
    rcv_program_change: int
    rcv_control_change: int
    rcv_poly_after_touch: int
    rcv_note_message: int
    rcv_rpn: int
    rcv_nrpn: int
    rcv_modulation: int
    rcv_volume: int
    rcv_pan: int
    rcv_expression: int
    rcv_hold_1: int
    rcv_portamento: int
    rcv_sostenuto: int
    rcv_soft_pedal: int

    mono_poly_mode: int
    same_note_number_key_on_assign: int
    part_mode: int
    note_shift: int
    detune: int
    volume: int
    velocity_sense_depth: int
    velocity_sense_offset: int
    pan: int
    note_limit_low: int
    note_limit_high: int
    ac_1_controller_number: int
    ac_2_controller_number: int
    dry_level: int
    chorus_send: int
    reverb_send: int
    variation_send: int

    vibrato_rate: int
    vibrato_depth: int
    filter_cutoff_frequency: int
    filter_resonance: int
    eg_attack_time: int
    eg_decay_time: int
    eg_release_time: int
    vibrato_delay: int

    scale_tuning_c: int
    scale_tuning_c_sharp: int
    scale_tuning_d: int
    scale_tuning_d_sharp: int
    scale_tuning_e: int
    scale_tuning_f: int
    scale_tuning_f_sharp: int
    scale_tuning_g: int
    scale_tuning_g_sharp: int
    scale_tuning_a: int
    scale_tuning_a_sharp: int
    scale_tuning_b: int

    mw_pitch_control: int
    mw_filter_control: int
    mw_amplitude_control: int
    mw_lfo_pmod_depth: int
    mw_lfo_fmod_depth: int

    bend_pitch_control: int
    bend_filter_control: int
    bend_amplitude_control: int
    bend_lfo_pmod_depth: int
    bend_lfo_fmod_depth: int

    cat_pitch_control: int
    cat_filter_control: int
    cat_amplitude_control: int
    cat_lfo_pmod_depth: int
    cat_lfo_fmod_depth: int

    pat_pitch_control: int
    pat_filter_control: int
    pat_amplitude_control: int
    pat_lfo_pmod_depth: int
    pat_lfo_fmod_depth: int

    ac_1_pitch_control: int
    ac_1_filter_control: int
    ac_1_amplitude_control: int
    ac_1_lfo_pmod_depth: int
    ac_1_lfo_fmod_depth: int

    ac_2_pitch_control: int
    ac_2_filter_control: int
    ac_2_amplitude_control: int
    ac_2_lfo_pmod_depth: int
    ac_2_lfo_fmod_depth: int

    portamento_switch: int
    portamento_time: int

    @classmethod
    def from_memory(cls, memory: list[int], part_number: int):
        entry_index = cls.PART_NUMBER_TO_ENTRY_INDEX_TABLE[part_number]
        entry_address = 0x008000 + (entry_index << 7)

        bank_select_msb = memory[entry_address + 0x01]
        bank_select_lsb = memory[entry_address + 0x02]
        program_number = memory[entry_address + 0x03]
        rcv_channel = memory[entry_address + 0x04]
        rcv_pitch_bend = memory[entry_address + 0x05]
        rcv_ch_after_touch = memory[entry_address + 0x06]
        rcv_program_change = memory[entry_address + 0x07]
        rcv_control_change = memory[entry_address + 0x08]
        rcv_poly_after_touch = memory[entry_address + 0x09]
        rcv_note_message = memory[entry_address + 0x0A]
        rcv_rpn = memory[entry_address + 0x0B]
        rcv_nrpn = memory[entry_address + 0x0C]
        rcv_modulation = memory[entry_address + 0x0D]
        rcv_volume = memory[entry_address + 0x0E]
        rcv_pan = memory[entry_address + 0x0F]
        rcv_expression = memory[entry_address + 0x10]
        rcv_hold_1 = memory[entry_address + 0x11]
        rcv_portamento = memory[entry_address + 0x12]
        rcv_sostenuto = memory[entry_address + 0x13]
        rcv_soft_pedal = memory[entry_address + 0x14]

        mono_poly_mode = memory[entry_address + 0x15]
        same_note_number_key_on_assign = memory[entry_address + 0x16]
        part_mode = memory[entry_address + 0x17]
        note_shift = memory[entry_address + 0x18]
        detune = ((memory[entry_address + 0x19] & 0x0F) << 4) | (
            memory[entry_address + 0x1A] & 0x0F
        )
        volume = memory[entry_address + 0x1B]
        velocity_sense_depth = memory[entry_address + 0x1C]
        velocity_sense_offset = memory[entry_address + 0x1D]
        pan = memory[entry_address + 0x1E]
        note_limit_low = memory[entry_address + 0x1F]
        note_limit_high = memory[entry_address + 0x20]
        ac_1_controller_number = memory[entry_address + 0x21]
        ac_2_controller_number = memory[entry_address + 0x22]
        dry_level = memory[entry_address + 0x23]
        chorus_send = memory[entry_address + 0x24]
        reverb_send = memory[entry_address + 0x25]
        variation_send = memory[entry_address + 0x26]

        vibrato_rate = memory[entry_address + 0x27]
        vibrato_depth = memory[entry_address + 0x28]
        filter_cutoff_frequency = memory[entry_address + 0x29]
        filter_resonance = memory[entry_address + 0x2A]
        eg_attack_time = memory[entry_address + 0x2B]
        eg_decay_time = memory[entry_address + 0x2C]
        eg_release_time = memory[entry_address + 0x2D]
        vibrato_delay = memory[entry_address + 0x2E]

        scale_tuning_c = memory[entry_address + 0x2F]
        scale_tuning_c_sharp = memory[entry_address + 0x30]
        scale_tuning_d = memory[entry_address + 0x31]
        scale_tuning_d_sharp = memory[entry_address + 0x32]
        scale_tuning_e = memory[entry_address + 0x33]
        scale_tuning_f = memory[entry_address + 0x34]
        scale_tuning_f_sharp = memory[entry_address + 0x35]
        scale_tuning_g = memory[entry_address + 0x36]
        scale_tuning_g_sharp = memory[entry_address + 0x37]
        scale_tuning_a = memory[entry_address + 0x38]
        scale_tuning_a_sharp = memory[entry_address + 0x39]
        scale_tuning_b = memory[entry_address + 0x3A]

        mw_pitch_control = memory[entry_address + 0x3B]
        mw_filter_control = memory[entry_address + 0x3C]
        mw_amplitude_control = memory[entry_address + 0x3D]
        mw_lfo_pmod_depth = memory[entry_address + 0x3E]
        mw_lfo_fmod_depth = memory[entry_address + 0x3F]

        bend_pitch_control = memory[entry_address + 0x41]
        bend_filter_control = memory[entry_address + 0x42]
        bend_amplitude_control = memory[entry_address + 0x43]
        bend_lfo_pmod_depth = memory[entry_address + 0x44]
        bend_lfo_fmod_depth = memory[entry_address + 0x45]

        cat_pitch_control = memory[entry_address + 0x47]
        cat_filter_control = memory[entry_address + 0x48]
        cat_amplitude_control = memory[entry_address + 0x49]
        cat_lfo_pmod_depth = memory[entry_address + 0x4A]
        cat_lfo_fmod_depth = memory[entry_address + 0x4B]

        pat_pitch_control = memory[entry_address + 0x4D]
        pat_filter_control = memory[entry_address + 0x4E]
        pat_amplitude_control = memory[entry_address + 0x4F]
        pat_lfo_pmod_depth = memory[entry_address + 0x50]
        pat_lfo_fmod_depth = memory[entry_address + 0x51]

        ac_1_pitch_control = memory[entry_address + 0x53]
        ac_1_filter_control = memory[entry_address + 0x54]
        ac_1_amplitude_control = memory[entry_address + 0x55]
        ac_1_lfo_pmod_depth = memory[entry_address + 0x56]
        ac_1_lfo_fmod_depth = memory[entry_address + 0x57]

        ac_2_pitch_control = memory[entry_address + 0x59]
        ac_2_filter_control = memory[entry_address + 0x5A]
        ac_2_amplitude_control = memory[entry_address + 0x5B]
        ac_2_lfo_pmod_depth = memory[entry_address + 0x5C]
        ac_2_lfo_fmod_depth = memory[entry_address + 0x5D]

        portamento_switch = memory[entry_address + 0x5F]
        portamento_time = memory[entry_address + 0x60]

        return cls(
            bank_select_msb,
            bank_select_lsb,
            program_number,
            rcv_channel,
            rcv_pitch_bend,
            rcv_ch_after_touch,
            rcv_program_change,
            rcv_control_change,
            rcv_poly_after_touch,
            rcv_note_message,
            rcv_rpn,
            rcv_nrpn,
            rcv_modulation,
            rcv_volume,
            rcv_pan,
            rcv_expression,
            rcv_hold_1,
            rcv_portamento,
            rcv_sostenuto,
            rcv_soft_pedal,
            mono_poly_mode,
            same_note_number_key_on_assign,
            part_mode,
            note_shift,
            detune,
            volume,
            velocity_sense_depth,
            velocity_sense_offset,
            pan,
            note_limit_low,
            note_limit_high,
            ac_1_controller_number,
            ac_2_controller_number,
            dry_level,
            chorus_send,
            reverb_send,
            variation_send,
            vibrato_rate,
            vibrato_depth,
            filter_cutoff_frequency,
            filter_resonance,
            eg_attack_time,
            eg_decay_time,
            eg_release_time,
            vibrato_delay,
            scale_tuning_c,
            scale_tuning_c_sharp,
            scale_tuning_d,
            scale_tuning_d_sharp,
            scale_tuning_e,
            scale_tuning_f,
            scale_tuning_f_sharp,
            scale_tuning_g,
            scale_tuning_g_sharp,
            scale_tuning_a,
            scale_tuning_a_sharp,
            scale_tuning_b,
            mw_pitch_control,
            mw_filter_control,
            mw_amplitude_control,
            mw_lfo_pmod_depth,
            mw_lfo_fmod_depth,
            bend_pitch_control,
            bend_filter_control,
            bend_amplitude_control,
            bend_lfo_pmod_depth,
            bend_lfo_fmod_depth,
            cat_pitch_control,
            cat_filter_control,
            cat_amplitude_control,
            cat_lfo_pmod_depth,
            cat_lfo_fmod_depth,
            pat_pitch_control,
            pat_filter_control,
            pat_amplitude_control,
            pat_lfo_pmod_depth,
            pat_lfo_fmod_depth,
            ac_1_pitch_control,
            ac_1_filter_control,
            ac_1_amplitude_control,
            ac_1_lfo_pmod_depth,
            ac_1_lfo_fmod_depth,
            ac_2_pitch_control,
            ac_2_filter_control,
            ac_2_amplitude_control,
            ac_2_lfo_pmod_depth,
            ac_2_lfo_fmod_depth,
            portamento_switch,
            portamento_time,
        )

    @staticmethod
    def to_mido_messages(
        partial: Union["MultiPartEntry", dict[str, int]],
        part_number: int,
        delta_time: int,
    ) -> list[mido.Message]:
        if isinstance(partial, MultiPartEntry):
            partial = asdict(partial)

        mido_messages: list[mido.Message] = []
        for key, value in partial.items():
            if key == "bank_select_msb":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x00,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "bank_select_lsb":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x20,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "program_number":
                mido_messages.append(
                    mido.Message(
                        "program_change",
                        channel=part_number,
                        program=value,
                        time=delta_time,
                    )
                )
            elif key == "volume":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x07,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "pan":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x0A,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "chorus_send":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x5D,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "reverb_send":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x5B,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "variation_send":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x5E,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "vibrato_rate":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x4C,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "vibrato_depth":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x4D,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "vibrato_delay":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x4E,
                        value=value,
                        time=delta_time,
                    )
                )
            elif key == "bend_pitch_control":
                mido_messages += [
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x65,
                        value=0x00,
                        time=delta_time,
                    ),
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x64,
                        value=0x00,
                    ),
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x06,
                        value=value - 0x40,
                    ),
                ]
            elif key == "sysex_portamento_switch":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x41,
                        value=0x00 if value == 0x00 else 0x7F,
                        time=delta_time,
                    )
                )
            elif key == "sysex_portamento_time":
                mido_messages.append(
                    mido.Message(
                        "control_change",
                        channel=part_number,
                        control=0x05,
                        value=value,
                        time=delta_time,
                    )
                )
        return mido_messages
