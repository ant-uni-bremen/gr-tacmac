#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest

# from gnuradio import blocks
from phy_layer import phy_layer


class qa_phy_layer(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        instance = phy_layer()

        self.assertTrue(instance.get_activate_cfo_compensation())
        instance.set_activate_cfo_compensation(False)
        self.assertFalse(instance.get_activate_cfo_compensation())

        self.assertTrue(instance.get_activate_phase_compensation())
        instance.set_activate_phase_compensation(False)
        self.assertFalse(instance.get_activate_phase_compensation())

        instance.set_cycle_interval(420e-6)
        self.assertAlmostEqual(instance.get_cycle_interval(), 420e-6)

        instance.set_timing_advance(256e-6)
        self.assertAlmostEqual(instance.get_timing_advance(), 256e-6)

        instance.set_ic_iterations(25)
        self.assertEqual(instance.get_ic_iterations(), 25)

        instance.set_scorr_threshold_low(.3)
        self.assertAlmostEqual(instance.get_scorr_threshold_low(), .3)

        instance.set_scorr_threshold_high(.4)
        self.assertAlmostEqual(instance.get_scorr_threshold_high(), .4)

        instance.set_xcorr_threshold(42.42)
        self.assertAlmostEqual(instance.get_xcorr_threshold(), 42.42)

        instance.set_tx_digital_gain(24.31)
        self.assertAlmostEqual(instance.get_tx_digital_gain(), 24.31)

        instance.set_carrier_freq(3.6e9)
        self.assertAlmostEqual(instance.get_carrier_freq(), 3.6e9)

        instance.set_rx_gain(25.)
        self.assertAlmostEqual(instance.get_rx_gain(), 25.)

        instance.set_tx_gain(16.)
        self.assertAlmostEqual(instance.get_tx_gain(), 16.)

    def test_001_descriptive_test_name(self):
        # set up fg
        self.tb.run()
        # check data


if __name__ == "__main__":
    gr_unittest.run(qa_phy_layer)