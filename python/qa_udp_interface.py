#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest
from udp_interface import udp_interface


class qa_udp_interface(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        instance = udp_interface(0, 64, 3, 84)

    def test_001_config(self):
        nports = 3
        instance = udp_interface(0, 56, nports, 84)
        self.assertEqual(len(instance._input_udp_blocks), nports)
        self.assertEqual(len(instance._output_udp_blocks), nports)
        self.assertEqual(len(instance._mac_controllers), nports)
        # set up fg
        self.tb.run()
        # check data


if __name__ == "__main__":
    gr_unittest.run(qa_udp_interface)
