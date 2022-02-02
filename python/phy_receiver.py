#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


from os import times
from gnuradio import gr, digital
from xfdm_sync import multi_port_sync_cc
from gfdm.pygfdm import get_gfdm_configuration
from gfdm import multi_port_receiver_cc
from tacmac import upper_phy_receiver
from polarwrap import get_polar_configuration


class phy_receiver(gr.hier_block2):
    """TACMAC PHY layer receiver

    This hierarchical receiver flowgraph should be the counterpart to the transmitter.
    It expects `num_antenna_ports` inputs.
    The number of outputs scales with the number of inputs.
    The `pdus` message output is the resulting received packet.
    Besides, we have the following outputs:
    - synced stream: input stream with fully synced tags
    - corr stream: correlation values for the synced stream
    - burst: extracted bursts from synced stream
    - estimate: Channel estimates for burts
    - symbol: Complex symbols
    """

    def __init__(
        self,
        num_antenna_ports,
        timeslots,
        subcarriers,
        active_subcarriers,
        bit_info_length,
        activate_cfo_compensation,
        activate_phase_compensation,
        ic_iterations,
        scorr_threshold_high,
        scorr_treshold_low,
        xcorr_threshold,
    ):
        gr.hier_block2.__init__(
            self,
            "phy_receiver",
            gr.io_signature(
                num_antenna_ports, num_antenna_ports, gr.sizeof_gr_complex
            ),  # Input signature
            gr.io_signature(
                5 * num_antenna_ports, 5 * num_antenna_ports, gr.sizeof_gr_complex
            ),
        )  # Output signature

        print(f"{num_antenna_ports=}, {timeslots=}, {subcarriers=}, {active_subcarriers=}, {bit_info_length=}")

        self.message_port_register_hier_out("pdus")

        rx_packet_start_key = "frame_start"
        rx_packet_length_key = "rx_len"

        cs_len = 8
        cp_len = 2 * cs_len
        if cp_len >= subcarriers:
            cp_len = subcarriers // 2
            cs_len = cp_len // 2

        gfdm_config = get_gfdm_configuration(
            timeslots,
            subcarriers,
            active_subcarriers,
            overlap=2,
            cp_len=cp_len,
            cs_len=cs_len,
            filtertype="rrc",
            filteralpha=0.2,
            cyclic_shifts=list(range(num_antenna_ports)),
        )
        import numpy as np
        for k, v in gfdm_config._asdict().items():
            if not isinstance(v, np.ndarray) and not isinstance(v, list):
                print(f"GFDM: {k:20}{v}")

        xcorr_compensate_freq_offset = True
        self.synchronizer = multi_port_sync_cc(
            num_antenna_ports,
            gfdm_config.core_preamble,
            scorr_threshold_high,
            scorr_treshold_low,
            xcorr_threshold,
            xcorr_compensate_freq_offset,
            rx_packet_start_key,
        )

        for port in range(num_antenna_ports):
            self.connect((self, port), (self.synchronizer, port))

            # synced streams
            self.connect((self.synchronizer, port), (self, port))

            # corr streams
            self.connect(
                (self.synchronizer, num_antenna_ports + port),
                (self, num_antenna_ports + port),
            )

        constellation = digital.constellation_calcdist(
            [-0.707 - 0.707j, -0.707 + 0.707j, 0.707 + 0.707j, 0.707 - 0.707j],
            [0, 1, 3, 2],
            4,
            1,
            digital.constellation.AMPLITUDE_NORMALIZATION,
        ).base()
        constellation_order = constellation.bits_per_symbol()
        # print(gfdm_config.core_preamble)

        channel_estimator_id = 1  # current, this option has no effect.
        map_resources_per_timeslot = True
        self.demodulator = multi_port_receiver_cc(
            num_antenna_ports,
            gfdm_config.timeslots,
            gfdm_config.subcarriers,
            gfdm_config.active_subcarriers,
            gfdm_config.overlap,
            gfdm_config.subcarrier_map,
            gfdm_config.cp_len,
            gfdm_config.cs_len,
            gfdm_config.rx_filter_taps,
            map_resources_per_timeslot,
            gfdm_config.core_preamble,
            channel_estimator_id,
            constellation,
            ic_iterations,
            activate_phase_compensation,
            activate_cfo_compensation,
            rx_packet_start_key,
        )

        for port in range(num_antenna_ports):
            self.connect((self.synchronizer, port), (self.demodulator, port))

            # burst streams
            self.connect(
                (self.demodulator, 2 * num_antenna_ports + port),
                (self, 2 * num_antenna_ports + port),
            )

            # estimate streams
            self.connect(
                (self.demodulator, num_antenna_ports + port),
                (self, 3 * num_antenna_ports + port),
            )

            # symbol streams
            self.connect((self.demodulator, port), (self, 4 * num_antenna_ports + port))

        interleaver_type = "convolutional"
        code_config = get_polar_configuration(
            constellation_order
            * gfdm_config.timeslots
            * gfdm_config.active_subcarriers,
            bit_info_length,
            interleaver_type=interleaver_type,
        )
        
        for k, v in code_config._asdict().items():
            if not isinstance(v, np.ndarray) and not isinstance(v, list):
                print(f"Code: {k:16}{v}")
        cnr_tag_key = "cnr"
        constellation_type = "GRAY"
        list_size = 8
        crc_len = 16
        decoder_type = "mixed"
        self.upper_phy = upper_phy_receiver(
            num_antenna_ports,
            constellation_order,
            code_config.frame_size,
            code_config.info_size,
            rx_packet_length_key,
            cnr_tag_key,
            constellation_type,
            list_size,
            crc_len,
            decoder_type,
        )
        
        for port in range(num_antenna_ports):
            self.connect((self.demodulator, port), (self.upper_phy, port))

        self.msg_connect((self.upper_phy, "pdus"), (self, "pdus"))

    def get_activate_cfo_compensation(self):
        return self.demodulator.get_activate_cfo_compensation()

    def set_activate_cfo_compensation(self, activate_cfo_compensation):
        self.demodulator.set_activate_cfo_compensation(activate_cfo_compensation)

    def get_ic_iterations(self):
        return self.demodulator.get_ic_iterations()

    def set_ic_iterations(self, ic_iterations):
        self.demodulator.set_ic_iterations(ic_iterations)

    def get_activate_phase_compensation(self):
        return self.demodulator.get_activate_phase_compensation()

    def set_activate_phase_compensation(self, activate_phase_compensation):
        self.demodulator.set_activate_phase_compensation(activate_phase_compensation)

    def get_scorr_threshold_high(self):
        return self.synchronizer.get_scorr_threshold_high()

    def set_scorr_threshold_high(self, scorr_threshold_high):
        self.synchronizer.set_scorr_threshold_high(scorr_threshold_high)

    def get_scorr_threshold_low(self):
        return self.synchronizer.get_scorr_threshold_low()

    def set_scorr_threshold_low(self, scorr_threshold_low):
        self.synchronizer.set_scorr_threshold_low(scorr_threshold_low)

    def get_xcorr_threshold(self):
        return self.synchronizer.get_xcorr_threshold()

    def set_xcorr_threshold(self, xcorr_threshold):
        self.synchronizer.set_xcorr_threshold(xcorr_threshold)