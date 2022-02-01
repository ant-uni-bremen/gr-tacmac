#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


from gnuradio import gr, blocks, fec
import symbolmapping
import polarwrap


class upper_phy_receiver(gr.hier_block2):
    """
    docstring for block upper_phy_receiver
    """

    def __init__(
        self,
        num_rx_streams,
        constellation_order,
        symbols_per_frame,
        bit_info_length,
        rx_packet_length_key="rx_len",
        cnr_tag_key="cnr",
        constellation_type="GRAY",
        list_size=8,
        crc_len=16,
        decoder_type="mixed",
    ):
        output_signature = [gr.sizeof_char,] + [
            gr.sizeof_float,
        ] * num_rx_streams
        gr.hier_block2.__init__(
            self,
            "upper_phy_receiver",
            gr.io_signature(num_rx_streams, num_rx_streams, gr.sizeof_gr_complex),
            gr.io_signature.makev(
                1 + num_rx_streams, 1 + num_rx_streams, output_signature
            ),
        )

        self.message_port_register_hier_out("pdus")

        assert bit_info_length % 8 == 0, "Bits per frame must be a byte multiple!"
        config = polarwrap.get_polar_configuration(
            constellation_order * symbols_per_frame,
            bit_info_length,
            interleaver_type="convolutional",
        )
        
        ##################################################
        # Symboldemapping
        ##################################################

        self.symbol_demappers = [
            symbolmapping.symbol_demapper_cf(
                constellation_order, constellation_type, f"{cnr_tag_key}{antenna_port}"
            )
            for antenna_port in range(num_rx_streams)
        ]

        for port in range(num_rx_streams):
            self.connect(
                (self, port),
                (self.symbol_demappers[port], 0),
            )

            self.connect(
                (self.symbol_demappers[port], 0),
                (self, 1 + port),
            )

        self.symbolmapping_interleaver = symbolmapping.interleaver_ff(
            config.interleaver_indices, True, False
        )

        decoder_object = polarwrap.decoderwrap.make(
            config.frame_size,
            list_size,
            config.frozen_bit_positions,
            crc_len,
            decoder_type,
        )
        self.fec_generic_decoder = fec.decoder(
            decoder_object, gr.sizeof_float, gr.sizeof_char
        )

        self.blocks_stream_to_tagged_stream = blocks.stream_to_tagged_stream(
            gr.sizeof_char, 1, config.frame_byte_size, rx_packet_length_key
        )

        self.blocks_tagged_stream_to_pdu = blocks.tagged_stream_to_pdu(
            blocks.byte_t, rx_packet_length_key
        )

        if num_rx_streams < 2:
            self.connect(
                (self.symbol_demappers[0], 0),
                (self.symbolmapping_interleaver, 0),
            )
        else:
            # Sum up all those pretty LLRs!
            self.blocks_add_xx = blocks.add_vff(1)

            for port in range(num_rx_streams):
                self.connect(
                    (self.symbol_demappers[port], 0),
                    (self.blocks_add_xx, port),
                )

            # The only required port! The combined LLR output.
            self.connect((self.blocks_add_xx, 0), (self.symbolmapping_interleaver, 0))

        self.connect(
            (self.symbolmapping_interleaver, 0),
            (self.fec_generic_decoder, 0),
            (self.blocks_stream_to_tagged_stream, 0),
            (self.blocks_tagged_stream_to_pdu, 0),
        )

        self.connect(
            (self.fec_generic_decoder, 0),
            (self, 0),
        )

        self.msg_connect((self.blocks_tagged_stream_to_pdu, "pdus"), (self, "pdus"))
