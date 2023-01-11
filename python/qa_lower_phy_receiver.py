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
    from lower_phy_receiver import lower_phy_receiver
except ImportError as e:
    print(f"Skipping with: {e}")


@unittest.skipIf("gfdm" not in sys.modules, reason="requires the gr-gfdm module")
class qa_lower_phy_receiver(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_001_instance_default(self):
        instance = lower_phy_receiver()

        instance.set_ic_iterations(4)
        self.assertEqual(instance.get_ic_iterations(), 4)

    def test_002_one_antenna(self):
        instance = lower_phy_receiver(nport=1)

        instance.set_ic_iterations(4)
        self.assertEqual(instance.get_ic_iterations(), 4)


if __name__ == "__main__":
    gr_unittest.run(qa_lower_phy_receiver)
