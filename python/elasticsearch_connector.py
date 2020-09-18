#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


import numpy
import time
from gnuradio import gr
import elasticsearch
import pmt

class elasticsearch_connector(gr.sync_block):
    """
    docstring for block elasticsearch_connector
    """
    def __init__(self, hostname='localhost', port=9200):
        gr.sync_block.__init__(self,
            name="elasticsearch_connector",
            in_sig=[],
            out_sig=[])
        self.message_port_register_in(pmt.mp("in"))
        self.set_msg_handler(pmt.mp("in"), self.handle_msg)
        dbname = f'{hostname}:{port}'
        self._db = elasticsearch.Elasticsearch([dbname, ])
        print(self._db.info())

    def handle_msg(self, msg):
        idx = pmt.symbol_to_string(pmt.car(msg))
        values = pmt.cdr(msg)

        if not pmt.is_dict(values):
            self._db.index(idx, body={"foo": str(pmt.to_python(values))})
            return

        body = {}
        for i in range(pmt.length(values)):
            k = str(pmt.to_python(pmt.car(pmt.nth(i, values))))
            v = pmt.cdr(pmt.nth(i, values))
            body[k] = str(pmt.to_python(v))
        self._db.index(idx, body=body)


    def work(self, input_items, output_items):
        in0 = input_items[0]
        out = output_items[0]
        # <+signal processing here+>
        out[:] = in0
        return len(output_items[0])
