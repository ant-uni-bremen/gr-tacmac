#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2019 Johannes Demel.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import tacmac
import pmt


class qa_tag_to_stream_value(gr_unittest.TestCase):
    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_001_t(self):
        tags = []
        ref = []
        for i in range(5):
            r = 1.0 * i + 1.0j * i
            ref.append(r)
            d = [
                i * 500,
                pmt.intern("phase"),
                pmt.from_complex(r),
                pmt.intern("testsource"),
            ]
            t = gr.tag_utils.python_to_tag(d)
            tags.append(t)

        t2s = tacmac.tag_to_stream_value_cc(8, "phase", "")
        src = blocks.vector_source_c([0.0j] * 10000, False, 1, tags)
        # hb = blocks.head(gr.sizeof_gr_complex, 4000)
        snk = blocks.vector_sink_c()
        self.tb.connect(src, t2s, snk)
        # set up fg
        self.tb.run()
        # check data
        #
        res = snk.data()
        print(res)
        self.assertComplexTuplesAlmostEqual(res, ref)

    def test_002_t(self):
        tags = []
        ref = []
        for i in range(5):
            r = 1.0 + 1.0 * i + 1.0j * i
            ref.append(r)
            v = pmt.make_dict()
            v = pmt.dict_add(v, pmt.intern("phase"), pmt.from_complex(r))
            d = [i * 500, pmt.intern("phase"), v, pmt.intern("testsource")]
            t = gr.tag_utils.python_to_tag(d)
            tags.append(t)

        t2s = tacmac.tag_to_stream_value_cc(8, "phase", "phase")
        src = blocks.vector_source_c([0.0j] * 10000, False, 1, tags)
        # hb = blocks.head(gr.sizeof_gr_complex, 4000)
        snk = blocks.vector_sink_c()
        self.tb.connect(src, t2s, snk)
        # set up fg
        self.tb.run()
        # check data
        #
        res = snk.data()
        print(res)
        self.assertComplexTuplesAlmostEqual(res, ref)

    def test_003_t(self):
        tags = []
        ref = []
        for i in range(5):
            r = 1.0 * i
            ref.append(r)
            d = [
                i * 500,
                pmt.intern("phase"),
                pmt.from_float(r),
                pmt.intern("testsource"),
            ]
            t = gr.tag_utils.python_to_tag(d)
            tags.append(t)

        t2s = tacmac.tag_to_stream_value_cf(8, "phase", "")
        src = blocks.vector_source_c([0.0j] * 10000, False, 1, tags)
        # hb = blocks.head(gr.sizeof_gr_complex, 4000)
        snk = blocks.vector_sink_f()
        self.tb.connect(src, t2s, snk)
        # set up fg
        self.tb.run()
        # check data
        #
        res = snk.data()
        print(res)
        self.assertFloatTuplesAlmostEqual(res, ref)

    def test_004_t(self):
        tags = []
        ref = []
        for i in range(5):
            r = i
            ref.append(r)
            d = [
                i * 500,
                pmt.intern("phase"),
                pmt.from_long(r),
                pmt.intern("testsource"),
            ]
            t = gr.tag_utils.python_to_tag(d)
            tags.append(t)

        t2s = tacmac.tag_to_stream_value_ci(8, "phase", "")
        src = blocks.vector_source_c([0.0j] * 10000, False, 1, tags)
        # hb = blocks.head(gr.sizeof_gr_complex, 4000)
        snk = blocks.vector_sink_i()
        self.tb.connect(src, t2s, snk)
        # set up fg
        self.tb.run()
        # check data
        #
        res = snk.data()
        print(res)
        self.assertTupleEqual(tuple(res), tuple(ref))


if __name__ == "__main__":
    gr_unittest.run(qa_tag_to_stream_value)
