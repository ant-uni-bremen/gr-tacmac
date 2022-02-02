#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


from gnuradio import gr, blocks, fec
import polarwrap
import symbolmapping


class upper_phy_transmitter(gr.hier_block2):
    """
    docstring for block upper_phy_transmitter
    """

    def __init__(
        self,
        constellation_order,
        frame_size,
        info_size,
        crc_len=16,
        packet_length_key="packet_len",
    ):
        gr.hier_block2.__init__(
            self,
            "upper_phy_transmitter",
            gr.io_signature(0, 0, 0),  # Input signature
            gr.io_signature(1, 1, gr.sizeof_gr_complex),
        )  # Output signature
        self.message_port_register_hier_in("pdus")
        # Define blocks and connect them
        self.pdu_to_tagged_stream = blocks.pdu_to_tagged_stream(
            blocks.byte_t, packet_length_key
        )
        self.msg_connect((self, "pdus"), (self.pdu_to_tagged_stream, "pdus"))

        config = polarwrap.get_polar_configuration(
            frame_size,
            info_size,
            interleaver_type="convolutional",
        )

        var_encoder = polarwrap.encoderwrap.make(
            frame_size, config.frozen_bit_positions, crc_len
        )

        self.fec_generic_encoder = fec.encoder(
            var_encoder, gr.sizeof_char, gr.sizeof_char
        )

        self.interleaver = symbolmapping.interleaver_bb(
            config.interleaver_indices, True, True
        )

        self.symbol_mapper = symbolmapping.symbol_mapper_bc(
            constellation_order, "GRAY", True
        )

        self.connect(
            (self.pdu_to_tagged_stream, 0),
            (self.fec_generic_encoder, 0),
            (self.interleaver, 0),
            (self.symbol_mapper, 0),
            (self, 0),
        )
