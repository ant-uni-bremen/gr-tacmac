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
import datetime

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

        self._db_device_id = f'{4711}'
        self._db_data_type = f'5gdata'
        self._common_body = {'type': self._db_data_type,
                             'deviceId': self._db_device_id}
        self._db_index = f'measurements-next-{datetime.date.today()}'
        self._db_doc_type = 'doc'

    def send_to_db(self, body):
        body.update(self._common_body)
        body['timestamp'] = datetime.datetime.now().timestamp()
        self._db.index(self._db_index, doc_type=self._db_doc_type, body=body)


    def handle_msg(self, msg):
        idx = pmt.symbol_to_string(pmt.car(msg))
        values = pmt.cdr(msg)

        if not pmt.is_dict(values):
            self.send_to_db({"foo": pmt.to_python(values)})
            # self._db.index(self._db_index, doc_type=self._db_doc_type, body={"foo": str(pmt.to_python(values))})
            return

        body = {}
        for i in range(pmt.length(values)):
            k = str(pmt.to_python(pmt.car(pmt.nth(i, values))))
            v = pmt.cdr(pmt.nth(i, values))
            if pmt.is_number(v):
                if pmt.is_complex(v):
                    body[f'qos.{k}.real'] = pmt.to_python(v).real
                    body[f'qos.{k}.imag'] = pmt.to_python(v).imag
                else:
                    body[f'qos.{k}'] = pmt.to_python(v)

        self.send_to_db(body)
        # self._db.index(self._db_index, doc_type=self._db_doc_type, body=body)


    def work(self, input_items, output_items):
        in0 = input_items[0]
        out = output_items[0]
        # <+signal processing here+>
        out[:] = in0
        return len(output_items[0])
