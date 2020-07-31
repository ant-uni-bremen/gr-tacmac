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
import numpy as np
try:
    from tacmac import tags_to_msg_dict
except ImportError:
    import os
    import sys
    dirname, filename = os.path.split(os.path.abspath(__file__))
    sys.path.append(os.path.join(dirname, "bindings"))
    from tacmac import tags_to_msg_dict

class qa_tags_to_msg_dict(gr_unittest.TestCase):

    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_instance(self):
        # FIXME: Test will fail until you pass sensible arguments to the constructor
        instance = tags_to_msg_dict(2)

    def test_001_descriptive_test_name(self):
        tag_key = 'energy_start'
        burst_len = 100
        n_frames = 5
        tags_per_frame = 3
        ref = np.array([], dtype=np.complex)
        tags = []
        for i in range(n_frames):
            frame = np.ones(burst_len) * (i + 1)
            ref = np.concatenate((ref, frame))
            for t in range(tags_per_frame):
                tag = gr.tag_t()
                tag.key = pmt.string_to_symbol(f'{tag_key}{i}{t}')
                tag.offset = burst_len * i
                tag.srcid = pmt.string_to_symbol('qa')
                tag.value = pmt.mp(f'foovalue{i}{t}')
                tags.append(tag)

        instance = tags_to_msg_dict(8)
        src = blocks.vector_source_c(ref, False, 1, tags)
        dbg = blocks.message_debug()
        self.tb.connect(src, instance)
        self.tb.msg_connect(instance, "out", dbg, "store")

        # set up fg
        self.tb.run()
        # check data
        self.assertEqual(dbg.num_messages(), n_frames)
        for i in range(n_frames):
            result_msg = dbg.get_message(i)
            print(i, ':', result_msg)
            self.assertEqual(pmt.length(result_msg), tags_per_frame)


if __name__ == '__main__':
    gr_unittest.run(qa_tags_to_msg_dict)
