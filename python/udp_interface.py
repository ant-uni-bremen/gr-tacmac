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
    The UDP interface is a hierarchical block to encapsulate the UDP connection and MAC.

    Internally, a number of UDP interfaces for TX and RX as well as MAC blocks are instantiated.
    However, all that complexity is encapsulated and only a fixed number of I/O ports are required.
    """

    def __init__(self, src_id, dst_id, nports, mtu_size):
        gr.hier_block2.__init__(
            self,
            "udp_interface",
            gr.io_signature(0, 0, 0),  # Input signature
            gr.io_signature(0, 0, 0),
        )  # Output signature
        self.logger = gr.logger(f"gr_log.{self.symbol_name()}")

        self.message_port_register_hier_in("rx")
        self.message_port_register_hier_out("tx")
        self.message_port_register_hier_out("timing")
        self.message_port_register_hier_out("status")

        self.logger.debug(
            f"src={src_id}, dst={dst_id}, nports={nports}, mtu_size={mtu_size}"
        )

        if src_id != 0 and nports > 1:
            raise RuntimeError(f"Invalid config! src={src_id} MUST be 0 for BS")
        portbase = 4000

        self._input_udp_blocks = []
        self._output_udp_blocks = []
        self._mac_controllers = []

        for port in range(nports):
            dev_dst_id = dst_id + port
            server_port = portbase + dst_id + port
            client_port = portbase + src_id + port
            self._mac_controllers.append(
                tacmac.mac_controller(dev_dst_id, src_id, mtu_size)
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
                    str(client_port),
                    mtu_size,
                    False,
                )
            )
            self.logger.debug(
                f"add {port=}\t{dev_dst_id} at UDP {server_port=}\t{client_port=}"
            )

            self._input_udp_blocks.append(
                blocks.socket_pdu("UDP_SERVER", "", str(server_port), mtu_size, False)
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
