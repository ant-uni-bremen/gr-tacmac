#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Johannes Demel.
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
import pmt
import numpy as np
import tacmac_swig as tacmac
import time

from PyCRC.CRCCCITT import CRCCCITT


def get_pdu_payload(payload):
    return pmt.init_u8vector(len(payload), payload)


def ndarray_to_pmt_u8vector(d):
    return pmt.init_u8vector(len(d),
                             np.array(d).astype(dtype=np.uint8).tolist())


def pmt_u8vector_to_ndarray(msg):
    return np.array(pmt.u8vector_elements(msg)).astype(dtype=np.uint8)


def get_hex_char_string(char_vec):
    return ' '.join('{:02x}'.format(i) for i in char_vec)


def string_to_int_list(s):
    lmsg = list(s)
    cmsg = [ord(c) for c in lmsg]
    return cmsg


def hex_string_to_int_list(s):
    s = s.replace(" ", "")
    l = map(''.join, zip(*[iter(s)]*2))
    h = [''.join(['0x', i, ]) for i in l]
    il = [int(i, 16) for i in h]
    return il


def get_int_from_pmt_meta(meta, key):
    return pmt.to_long(pmt.dict_ref(meta, pmt.intern(key), pmt.PMT_NIL))


def generate_phy_frame(ndpayload, dst, src, sequence, timestamp):
    header = np.zeros(13, dtype=np.uint8)
    header[0] = dst
    header[1] = src
    ndsequence = np.array([sequence, ], dtype=np.uint16).view('>u1')[::-1]
    header[2:4] = ndsequence
    header[4] = ndpayload.size
    ndtimestamp = np.array([timestamp, ], dtype=np.uint64).view('>u1')[::-1]
    header[5:13] = ndtimestamp
    ndpayload = np.concatenate((header, ndpayload))
    checksum = CRCCCITT(version='FFFF').calculate(ndpayload.tobytes())
    # print(checksum)
    ndchecksum = np.array([checksum, ], dtype=np.uint16)
    ndchecksum = ndchecksum.view('>u1')[::-1]
    # print(ndchecksum)
    # print(' '.join(hex(i) for i in ndchecksum))
    ndpayload = np.concatenate((ndpayload, ndchecksum))
    # print(ndpayload)
    # return
    return ndpayload


class qa_mac_controller(gr_unittest.TestCase):

    def setUp(self):
        self.tb = gr.top_block()

    def tearDown(self):
        self.tb = None

    def test_001_init(self):
        return
        self.assertRaises(RuntimeError, tacmac.mac_controller, 450, 21, 112)
        self.assertRaises(RuntimeError, tacmac.mac_controller, 42, 768, 112)
        self.assertRaises(RuntimeError, tacmac.mac_controller, 42, 84, 427)

    def test_002_llc2phy(self):
        return
        num_pdus = 340
        dst_id = 42
        src_id = 21
        msg = u"Sample message for frame formatter Yihhaaa"
        message = string_to_int_list(msg)
        payload = get_pdu_payload(message)

        ref = pmt_u8vector_to_ndarray(payload)

        meta = pmt.make_dict()
        pdu = pmt.cons(meta, payload)

        print('This is the orriginal PDU\n----------------')
        print(pdu)
        print('----------------')
        ctrl = tacmac.mac_controller(dst_id, src_id, len(payload) - 1)
        dbg = blocks.message_debug()

        self.tb.msg_connect(ctrl, "PHYout", dbg, "store")
        # self.tb.msg_connect(ctrl, "PHYout", dbg, "print_pdu")

        self.tb.start()

        for i in range(num_pdus):
            # eww, what's that smell?
            ctrl.to_basic_block()._post(pmt.intern("LLCin"), pdu)

        while dbg.num_messages() < num_pdus:
            pass
        self.tb.stop()
        self.tb.wait()

        for i in range(num_pdus):
            result_msg = dbg.get_message(i)
            meta = pmt.car(result_msg)
            bits = pmt.cdr(result_msg)
            pl = pmt_u8vector_to_ndarray(bits)

            header = pl[0:12]
            self.assertEqual(header[0], dst_id)
            self.assertEqual(header[1], src_id)
            self.assertEqual(get_int_from_pmt_meta(meta, 'dst_id'), dst_id)
            self.assertEqual(get_int_from_pmt_meta(meta, 'src_id'), src_id)
            parsed_sequence = int(header.view('>u2')[1])
            self.assertEqual(get_int_from_pmt_meta(meta, 'sequence'),
                             parsed_sequence)
            mtime = get_int_from_pmt_meta(meta, 'time')
            tbytes = header[4:12]
            htime = int(tbytes.view('>u8')[0])
            self.assertEqual(mtime, htime)
            checksum = pl[-2:]
            # print(checksum)
            checksum = int(checksum.view('>u2'))
            # print(checksum)
            r = CRCCCITT(version='FFFF').calculate(pl[:-2].tobytes())
            # print(r)
            self.assertEqual(r, checksum)
            self.assertSequenceEqual(tuple(pl[12:-2]), tuple(ref))

    def test_003_phy2llc(self):
        num_pdus = 700
        dst_id = 42
        src_id = 21
        msg = u"Sample message for frame formatter Yihhaaa"
        message = string_to_int_list(msg)
        payload = get_pdu_payload(message)
        ndpayload = pmt_u8vector_to_ndarray(payload)
        print(ndpayload)

        meta = pmt.make_dict()
        pdu = pmt.cons(meta, payload)

        print('This is the orriginal PDU\n----------------')
        print(pdu)
        print('----------------')
        ctrl = tacmac.mac_controller(
            src_id, dst_id, pmt.uniform_vector_itemsize(payload))
        dbg = blocks.message_debug()

        self.tb.msg_connect(ctrl, "LLCout", dbg, "store")
        self.tb.msg_connect(ctrl, "PHYout", dbg, "print_pdu")

        self.tb.start()

        timestamps = np.zeros(num_pdus, dtype=np.uint64)
        for i in range(num_pdus):
            timestamp = np.uint64(time.time() * 1e9)
            timestamps[i] = timestamp
            phypayload = generate_phy_frame(ndpayload, dst_id,
                                            src_id, i, timestamp)
            payload = ndarray_to_pmt_u8vector(phypayload)
            meta = pmt.make_dict()
            pdu = pmt.cons(meta, payload)
            # eww, what's that smell?
            ctrl.to_basic_block()._post(pmt.intern("PHYin"), pdu)

        while dbg.num_messages() < num_pdus:
            pass
        self.tb.stop()
        self.tb.wait()

        for i in range(num_pdus):
            result_msg = dbg.get_message(i)
            meta = pmt.car(result_msg)
            # print(meta)
            bits = pmt.cdr(result_msg)
            data = pmt_u8vector_to_ndarray(bits)
            self.assertSequenceEqual(tuple(ndpayload), tuple(data))

            self.assertEqual(get_int_from_pmt_meta(meta, 'dst_id'),
                             dst_id)
            self.assertEqual(get_int_from_pmt_meta(meta, 'src_id'),
                             src_id)
            self.assertEqual(get_int_from_pmt_meta(meta, 'sequence'),
                             i % int(2 ** 16))
            self.assertEqual(get_int_from_pmt_meta(meta, 'lost_packets'), 0)

            mtime = get_int_from_pmt_meta(meta, 'time')
            self.assertEqual(mtime, timestamps[i])
            self.assertGreater(get_int_from_pmt_meta(meta, 'latency'), 0)


if __name__ == '__main__':
    gr_unittest.run(qa_mac_controller)
