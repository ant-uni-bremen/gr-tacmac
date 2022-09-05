#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import blocks
from gnuradio import gr
from gnuradio import fec
import polarwrap
import symbolmapping
import gfdm
import grtypes


class phy_transmitter(gr.hier_block2):
    """
    TACMAC PHY transmitter

    Input: PDUs with data
    Output: N antenna streams with CDD frames
    """

    def __init__(
        self,
        timeslots=15,
        subcarriers=64,
        active_subcarriers=60,
        overlap=2,
        subcarrier_map=list(range(60)),
        cp_len=16,
        cs_len=8,
        ramp_len=8,
        frequency_domain_taps=list(range(30)),
        constellation_order=2,
        window_taps=list(range(16)),
        frame_size=1024,
        frozen_bit_positions=list(range(512)),
        interleaver_indices=list(range(1024)),
        pre_padding=256,
        post_padding=128,
        full_preambles=[
            list(range(146)),
            list(range(146)),
        ],
        cycle_interval=320.0e-6,
        timing_advance=2.0e-4,
        tx_digital_gain=2.7,
        cyclic_shift=[
            0,
            2,
        ],
        packet_length_key="packet_len",
        use_timed_commands=True,
        enable_tx_latency_reporting=False,
    ):
        gr.hier_block2.__init__(
            self,
            "phy_transmitter",
            gr.io_signature(0, 0, 0),  # Input signature
            gr.io_signature(len(cyclic_shift), len(cyclic_shift), gr.sizeof_gr_complex),
        )  # Output signature
        self.logger = gr.logger(f"gr_log.{self.symbol_name()}")
        self.logger.debug(f"{use_timed_commands=}, {enable_tx_latency_reporting=}")

        assert len(cyclic_shift) == len(full_preambles)

        self.message_port_register_hier_in("pdus")
        self.message_port_register_hier_in("time_tag")
        self.message_port_register_hier_out("command")

        ##################################################
        # Variables
        ##################################################
        var_encoder = polarwrap.encoderwrap.make(frame_size, frozen_bit_positions, 0)

        ##################################################
        # Blocks
        ##################################################
        self.blocks_pdu_to_tagged_stream = blocks.pdu_to_tagged_stream(
            grtypes.byte_t, packet_length_key
        )

        self.fec_generic_encoder = fec.encoder(
            var_encoder, gr.sizeof_char, gr.sizeof_char
        )

        self.symbolmapping_interleaver = symbolmapping.interleaver_bb(
            interleaver_indices, True, True
        )

        self.symbolmapping_symbol_mapper_bc = symbolmapping.symbol_mapper_bc(
            constellation_order, "GRAY", True
        )

        self.gfdm_transmitter_cc = gfdm.transmitter_cc(
            timeslots,
            subcarriers,
            active_subcarriers,
            cp_len,
            cs_len,
            ramp_len,
            subcarrier_map,
            True,
            overlap,
            frequency_domain_taps,
            window_taps,
            cyclic_shift,
            full_preambles,
            packet_length_key,
        )
        self.gfdm_short_burst_shaper = gfdm.short_burst_shaper(
            pre_padding,
            post_padding,
            tx_digital_gain,
            len(cyclic_shift),
            packet_length_key,
            use_timed_commands,
            timing_advance,
            cycle_interval,
            enable_tx_latency_reporting,
        )

        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self, "pdus"), (self.blocks_pdu_to_tagged_stream, "pdus"))
        self.connect(
            (self.blocks_pdu_to_tagged_stream, 0),
            (self.fec_generic_encoder, 0),
            (self.symbolmapping_interleaver, 0),
            (self.symbolmapping_symbol_mapper_bc, 0),
            (self.gfdm_transmitter_cc, 0),
        )

        for port in range(len(cyclic_shift)):
            self.connect(
                (self.gfdm_transmitter_cc, port), (self.gfdm_short_burst_shaper, port)
            )
            self.connect((self.gfdm_short_burst_shaper, port), (self, port))

        self.msg_connect((self.gfdm_short_burst_shaper, "command"), (self, "command"))

        self.msg_connect((self, "time_tag"), (self.gfdm_short_burst_shaper, "time_tag"))

    def get_cycle_interval(self):
        return self.gfdm_short_burst_shaper.cycle_interval()

    def set_cycle_interval(self, cycle_interval):
        self.gfdm_short_burst_shaper.set_cycle_interval(cycle_interval)

    def get_timing_advance(self):
        return self.gfdm_short_burst_shaper.timing_advance()

    def set_timing_advance(self, timing_advance):
        self.gfdm_short_burst_shaper.set_timing_advance(timing_advance)

    def get_tx_digital_gain(self):
        return self.gfdm_short_burst_shaper.scale()

    def set_tx_digital_gain(self, tx_digital_gain):
        self.gfdm_short_burst_shaper.set_scale(tx_digital_gain)
