#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import pmt
from tacmac import status_collector


class qa_status_collector(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        # FIXME: Test will fail until you pass sensible arguments to the constructor
        instance = status_collector()

    def test_001_descriptive_test_name(self):
        test_messages = [pmt.mp("wtf")]
        instance = status_collector()
        dbg = blocks.message_debug()

        self.tb.msg_connect(instance, "out", dbg, "store")
        # self.tb.msg_connect(ctrl, "PHYout", dbg, "print_pdu")

        self.tb.start()

        for m in test_messages:
            # eww, what's that smell?
            instance.to_basic_block()._post(pmt.intern("in"), m)

        while dbg.num_messages() < len(test_messages):
            pass
        self.tb.stop()
        self.tb.wait()


if __name__ == "__main__":
    gr_unittest.run(qa_status_collector)
