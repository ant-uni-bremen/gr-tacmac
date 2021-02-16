#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020, 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


import numpy
import datetime
import elasticsearch
from elasticbatch import ElasticBuffer
from gnuradio import gr
import pmt
import socket


class elasticsearch_connector(gr.sync_block):
    """
    ElasticSearch Connector.

    Send flowgraph state data to a database.
    Here we need to
    1. Connect to the correct database
    2. Set some metadata correctly
    3. Format data correctly to be sent to the database.
    4. Send data. Take care of correct transmission properties.
    """

    def __init__(self, hostname='localhost', port=9200, device_id=4711,
                 data_type='5gdata', index_prefix='measurements-',
                 buffer_size=5000):
        gr.sync_block.__init__(self,
                               name="elasticsearch_connector",
                               in_sig=[],
                               out_sig=[])
        self.message_port_register_in(pmt.mp("in"))
        self.set_msg_handler(pmt.mp("in"), self.handle_msg)

        self._hostname = socket.gethostname()
        # set up database connection
        dbname = f'{hostname}:{port}'
        client_kwargs = {'hosts': dbname}

        # Configure common metadata
        self._db_device_id = f'{device_id}'
        self._db_data_type = f'{data_type}'
        self._common_body = {'type': self._db_data_type,
                             'deviceId': self._db_device_id}

        # Configure database.
        self._db_index = f'{index_prefix}{datetime.date.today()}'
        self._db_doc_type = 'doc'

        def index_func(doc):
            return self._db_index

        def data_type_func(doc):
            return self._db_data_type

        def device_id_func(doc):
            return self._db_device_id

        def hostname_func(doc):
            return self._hostname

        def timestamp_func(doc):
            return int(1e3 * datetime.datetime.now().timestamp())

        self._db_buffer = ElasticBuffer(client_kwargs=client_kwargs,
                                        _index=index_func,
                                        type=data_type_func,
                                        deviceId=device_id_func,
                                        timestamp=timestamp_func,
                                        hostname=hostname_func,
                                        size=buffer_size)

    def send_to_buffer(self, body):
        self._db_buffer.add([body, ])
        if self._db_buffer.oldest_elapsed_time > 10.0:
            # Just flush if we buffered for more than 10.0s.
            # This is a fixed threshold for now.
            self._db_buffer.flush()

    def handle_msg(self, msg):
        meta = pmt.symbol_to_string(pmt.car(msg))
        direction = 'unknown'
        if 'rx' in meta:
            direction = 'rx'
        elif 'tx' in meta:
            direction = 'tx'
        values = pmt.cdr(msg)

        if not pmt.is_dict(values):
            self.send_to_buffer({"foo": pmt.to_python(values)})
            return

        body = {'direction': direction}
        for i in range(pmt.length(values)):
            k = str(pmt.to_python(pmt.car(pmt.nth(i, values))))
            v = pmt.cdr(pmt.nth(i, values))
            if pmt.is_number(v):
                if pmt.is_complex(v):
                    body[f'qos.{k}.real'] = pmt.to_python(v).real
                    body[f'qos.{k}.imag'] = pmt.to_python(v).imag
                else:
                    body[f'qos.{k}'] = pmt.to_python(v)
        self.send_to_buffer(body)

    def work(self, input_items, output_items):
        # No signal processing! This should never happen!
        # This is a message only block!
        return len(output_items[0])
