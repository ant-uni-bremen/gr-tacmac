#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import sys
import unittest
from gnuradio import gr, gr_unittest
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
        instance = phy_receiver(2, 15, 64, 60, 792, True, True, 4, 0.98, 0.95, 30.0)
        instance.set_activate_cfo_compensation(True)
        instance.set_activate_cfo_compensation(False)

        empty_pilots = instance.pilots()
        self.assertEqual(len(empty_pilots), 0)

        pilots = ((10, 0, 1+1j), (56, 0, -1-1j))
        instance.set_pilots(pilots)
        used_pilots = instance.pilots()

        for ref, used in zip(pilots, used_pilots):
            self.assertEqual(ref[0], used[0])
            self.assertEqual(ref[1], used[1])
            self.assertComplexAlmostEqual(ref[2], used[2])

    def test_001_descriptive_test_name(self):
        # set up fg
        self.tb.run()
        # check data


if __name__ == "__main__":
    gr_unittest.run(qa_phy_receiver)
