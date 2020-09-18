#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import gr, gr_unittest
# from gnuradio import blocks
from elasticsearch_connector import elasticsearch_connector
import pmt

class qa_elasticsearch_connector(gr_unittest.TestCase):

    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        # FIXME: Test will fail until you pass sensible arguments to the constructor
        instance = elasticsearch_connector()

    def test_001_descriptive_test_name(self):
        # set up fg
        pdu = pmt.cons(pmt.mp('test'), pmt.make_dict())
        instance = elasticsearch_connector()
        self.tb.run()
        instance.to_basic_block()._post(pmt.intern("in"), pdu)


        # check data


if __name__ == '__main__':
    gr_unittest.run(qa_elasticsearch_connector)
