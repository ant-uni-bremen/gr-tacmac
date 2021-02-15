#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2020 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#


from gnuradio import gr
from gnuradio import blocks
import tacmac


class udp_interface(gr.hier_block2):
    """
    docstring for block udp_interface
    """

    def __init__(self, src_id, dst_id, nports, mtu_size):
        gr.hier_block2.__init__(
            self,
            "udp_interface",
            gr.io_signature(0, 0, 0),  # Input signature
            gr.io_signature(0, 0, 0),
        )  # Output signature

        self.message_port_register_hier_in("rx")
        self.message_port_register_hier_out("tx")
        self.message_port_register_hier_out("timing")
        self.message_port_register_hier_out("status")
        print(f'udp interface src={src_id}, dst={dst_id}, nports={nports}, mtu_size={mtu_size}')

        if src_id != 0 and nports > 1:
            raise RuntimeError(f"Invalid config! src={src_id} MUST be 0 for BS")
        portbase = 4000

        self._input_udp_blocks = []
        self._output_udp_blocks = []
        self._mac_controllers = []

        for port in range(nports):
            self._mac_controllers.append(
                tacmac.mac_controller(dst_id + port, src_id, mtu_size)
            )
            self.msg_connect((self._mac_controllers[port], "PHYout"), (self, "tx"))
            self.msg_connect((self, "rx"), (self._mac_controllers[port], "PHYin"))
            if src_id > 0:
                self.msg_connect(
                    (self._mac_controllers[port], "timing"), (self, "timing")
                )

            self._output_udp_blocks.append(
                blocks.socket_pdu(
                    "UDP_CLIENT",
                    "localhost",
                    str(portbase + src_id + port),
                    mtu_size,
                    False,
                )
            )
            print(port, str(portbase + dst_id + port))

            self._input_udp_blocks.append(
                blocks.socket_pdu(
                    "UDP_SERVER", "", str(portbase + dst_id + port), mtu_size, False
                )
            )

            self.msg_connect(
                (self._input_udp_blocks[port], "pdus"),
                (self._mac_controllers[port], "LLCin"),
            )
            self.msg_connect(
                (self._mac_controllers[port], "LLCout"),
                (self._output_udp_blocks[port], "pdus"),
            )
            self.msg_connect(
                (self._mac_controllers[port], "LLCout"),
                (self, "status"),
            )
            
            
