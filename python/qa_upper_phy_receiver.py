#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest, blocks
from upper_phy_receiver import upper_phy_receiver
from upper_phy_transmitter import upper_phy_transmitter
import numpy as np
import pypolar
import symbolmapping
from polarwrap import get_polar_configuration
import pmt
import grtypes


def encode_frame(bits, block_len, punctured_len, crc_len, frozen_bit_positions):
    detector = pypolar.Detector(crc_len, "CRC")
    encoder = pypolar.PolarEncoder(block_len, frozen_bit_positions)
    encoder.setErrorDetection(0)
    puncturer = pypolar.Puncturer(punctured_len, frozen_bit_positions)

    d = np.packbits(bits)
    crcd = detector.generate(d)
    frame = encoder.encode_vector(crcd)
    frame = puncturer.puncturePacked(frame)
    return frame


class qa_upper_phy_receiver(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        instance = upper_phy_receiver(2, 2, 1800, 792)

    def test_001_single_rx_stream(self):
        constellation_order = 2
        symbols_per_frame = 900
        punctured_len = constellation_order * symbols_per_frame
        info_len = 792
        crc_len = 16
        config = get_polar_configuration(
            punctured_len, info_len, interleaver_type="convolutional"
        )

        bits = np.random.randint(0, 2, config.info_size - crc_len).astype(np.int32)
        frame = encode_frame(
            bits,
            config.block_size,
            config.frame_size,
            crc_len,
            config.frozen_bit_positions,
        )
        frame = np.unpackbits(frame)

        interleaver = symbolmapping.Interleaver(config.interleaver_indices)
        mapper = symbolmapping.SymbolMapping(constellation_order)
        interleaved = interleaver.interleave(frame)
        symbols = mapper.map_to_constellation(interleaved)

        src = blocks.vector_source_c(symbols)
        instance = upper_phy_receiver(
            1, constellation_order, config.frame_size, config.info_size
        )
        snk = blocks.vector_sink_b()
        self.tb.connect(src, instance, snk)
        self.tb.run()

        result = np.array(snk.data())
        reference = np.packbits(bits)
        np.testing.assert_equal(result[:-2], reference)

    def test_002_4_rx_stream(self):
        constellation_order = 2
        symbols_per_frame = 900
        punctured_len = constellation_order * symbols_per_frame
        info_len = 792
        crc_len = 16
        config = get_polar_configuration(
            punctured_len, info_len, interleaver_type="convolutional"
        )

        bits = np.random.randint(0, 2, config.info_size - crc_len).astype(np.int32)
        frame = encode_frame(
            bits,
            config.block_size,
            config.frame_size,
            crc_len,
            config.frozen_bit_positions,
        )
        frame = np.unpackbits(frame)

        interleaver = symbolmapping.Interleaver(config.interleaver_indices)
        mapper = symbolmapping.SymbolMapping(constellation_order)
        interleaved = interleaver.interleave(frame)
        symbols = mapper.map_to_constellation(interleaved)

        srcs = [blocks.vector_source_c(symbols) for _ in range(4)]
        instance = upper_phy_receiver(
            4, constellation_order, config.frame_size, config.info_size
        )
        snk = blocks.vector_sink_b()
        llrs = [blocks.vector_sink_f() for _ in range(4)]

        for i in range(4):
            self.tb.connect((srcs[i], 0), (instance, i))
            self.tb.connect((instance, i + 1), (llrs[i], 0))
        self.tb.connect((instance, 0), snk)

        sumllrs = blocks.vector_sink_f()
        self.tb.connect((instance.blocks_add_xx, 0), sumllrs)

        self.tb.run()

        result = np.array(snk.data())
        reference = np.packbits(bits)
        np.testing.assert_equal(result[:-2], reference)

        bitref = np.sign(1.0 - 2.0 * interleaved)
        summed = np.zeros_like(bitref)
        for l in llrs:
            res = np.array(l.data())
            summed += res
            np.testing.assert_equal(np.sign(res), bitref)

        summed_llrs = np.array(sumllrs.data())
        np.testing.assert_equal(summed, summed_llrs)

    def test_003_transceiver_integration(self):
        constellation_order = 2
        frame_size = 1800
        info_len = 792
        crc_len = 16
        config = get_polar_configuration(
            frame_size, info_len, interleaver_type="convolutional"
        )

        bits = np.random.randint(0, 2, config.info_size - crc_len).astype(np.int32)
        packed_bits = np.packbits(bits).astype(np.uint8)

        src = blocks.vector_source_b(packed_bits)
        tagger = blocks.stream_to_tagged_stream(
            gr.sizeof_char, 1, packed_bits.size, "foo"
        )
        topdu = blocks.tagged_stream_to_pdu(grtypes.byte_t, "foo")
        self.tb.connect(src, tagger, topdu)

        transmitter = upper_phy_transmitter(
            constellation_order, config.frame_size, config.info_size, crc_len, "test"
        )
        self.tb.msg_connect((topdu, "pdus"), (transmitter, "pdus"))
        snk = blocks.vector_sink_c()
        self.tb.connect(transmitter, snk)

        receiver = upper_phy_receiver(
            4, constellation_order, config.frame_size, config.info_size, crc_len=crc_len
        )
        for i in range(4):
            self.tb.connect((transmitter, 0), (receiver, i))

        dbg = blocks.message_debug()
        self.tb.msg_connect(receiver, "pdus", dbg, "store")
        self.tb.run()
        for i in range(dbg.num_messages()):
            msg = dbg.get_message(i)
            meta = pmt.to_python(pmt.car(msg))
            bits = pmt.to_python(pmt.cdr(msg))
            np.testing.assert_equal(bits[:-2], packed_bits)


if __name__ == "__main__":
    gr_unittest.run(qa_upper_phy_receiver)
