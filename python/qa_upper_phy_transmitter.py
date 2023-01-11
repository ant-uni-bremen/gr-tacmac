#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys
import unittest
import numpy as np
from gnuradio import gr, gr_unittest, blocks
import grtypes
try:
    from upper_phy_transmitter import upper_phy_transmitter
    from polarwrap import get_polar_configuration
    import symbolmapping
    import pypolar
except ImportError as e:
    print(f"Skipping with: {e}")


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


@unittest.skipIf("polarwrap" not in sys.modules, reason="requires the gr-polarwrap module")
class qa_upper_phy_transmitter(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        # FIXME: Test will fail until you pass sensible arguments to the constructor
        instance = upper_phy_transmitter(2, 1800, 792, 0, "test")

    def test_001_transmit(self):
        constellation_order = 2
        frame_size = 1800
        info_len = 792
        crc_len = 16
        config = get_polar_configuration(
            frame_size, info_len, interleaver_type="convolutional"
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

        packed_bits = np.packbits(bits).astype(np.uint8)

        src = blocks.vector_source_b(packed_bits)
        tagger = blocks.stream_to_tagged_stream(
            gr.sizeof_char, 1, packed_bits.size, "foo"
        )
        topdu = blocks.tagged_stream_to_pdu(grtypes.byte_t, "foo")
        self.tb.connect(src, tagger, topdu)

        instance = upper_phy_transmitter(
            constellation_order, config.frame_size, config.info_size, crc_len, "test"
        )
        self.tb.msg_connect((topdu, "pdus"), (instance, "pdus"))
        snk = blocks.vector_sink_c()
        self.tb.connect(instance, snk)
        self.tb.run()

        result = np.array(snk.data())
        self.assertComplexTuplesAlmostEqual(result, symbols)


if __name__ == "__main__":
    gr_unittest.run(qa_upper_phy_transmitter)
