#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys
import unittest
from gnuradio import gr, gr_unittest
try:
    from phy_transmitter import phy_transmitter
except ImportError as e:
    print(f"Skipping with: {e}")


@unittest.skipIf(
    "polarwrap" not in sys.modules, reason="requires the gr-polarwrap module"
)
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

        empty_pilots = instance.pilots()
        self.assertEqual(len(empty_pilots), 0)

        pilots = ((10, 0, 1+1j), (56, 0, -1-1j))
        instance.set_pilots(pilots)
        used_pilots = instance.pilots()

        for ref, used in zip(pilots, used_pilots):
            self.assertEqual(ref[0], used[0])
            self.assertEqual(ref[1], used[1])
            self.assertComplexAlmostEqual(ref[2], used[2])


if __name__ == "__main__":
    gr_unittest.run(qa_phy_transmitter)
