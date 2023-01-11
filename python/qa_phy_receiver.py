#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys
from gnuradio import gr, gr_unittest
import unittest

# from gnuradio import blocks
try:
    from phy_receiver import phy_receiver
except ImportError as e:
    print(f"Skipping with: {e}")


@unittest.skipIf("gfdm" not in sys.modules, reason="requires the gr-gfdm module")
class qa_phy_receiver(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        # FIXME: Test will fail until you pass sensible arguments to the constructor
        instance = phy_receiver(2, 15, 64, 60, 792, True, True, 4, 0.98, 0.95, 30.0)
        instance.set_activate_cfo_compensation(True)
        instance.set_activate_cfo_compensation(False)

    def test_001_descriptive_test_name(self):
        # set up fg
        self.tb.run()
        # check data


if __name__ == "__main__":
    gr_unittest.run(qa_phy_receiver)
