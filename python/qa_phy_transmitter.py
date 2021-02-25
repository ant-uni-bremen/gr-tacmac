#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest

# from gnuradio import blocks
from phy_transmitter import phy_transmitter


class qa_phy_transmitter(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_001_instance(self):
        instance = phy_transmitter()

        instance.set_cycle_interval(256e-6)
        self.assertAlmostEqual(instance.get_cycle_interval(), 256e-6)

        instance.set_timing_advance(364.5e-6)
        self.assertAlmostEqual(instance.get_timing_advance(), 364.5e-6)

        instance.set_tx_digital_gain(42.5)
        self.assertAlmostEqual(instance.get_tx_digital_gain(), 42.5)


if __name__ == "__main__":
    gr_unittest.run(qa_phy_transmitter)
