#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest
import tacmac


class qa_periodic_time_tag_cc(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_001_t(self):
        # set up fg
        tagger = tacmac.periodic_time_tag_cc(30.72e6, 420)
        self.tb.run()
        # check data


if __name__ == "__main__":
    gr_unittest.run(qa_periodic_time_tag_cc)
