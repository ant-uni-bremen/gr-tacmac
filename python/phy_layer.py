#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import time
import numpy as np
from gnuradio import gr
from gnuradio import uhd
from gnuradio import digital
from gnuradio import blocks
from gnuradio import fec
import tacmac
import polarwrap
import symbolmapping
from gfdm.pygfdm import get_gfdm_configuration


def parse_usrp_address(addr):
    uhd_keywords = ["serial", "addr", "resource", "name", "type", "vid", "pid"]
    for k in uhd_keywords:
        # we expect plain IP addresses. Otherwise, prefer user input.
        if k in addr:
            return addr
    return ",".join(
        [f"addr{i}={a}" for i, a in enumerate(addr.replace(",", " ").split())]
    )


class phy_layer(gr.hier_block2):
    """
    PHY layer for polar GFDM demo
    """

    def __init__(
        self,
        timeslots=15,
        subcarriers=64,
        active_subcarriers=60,
        activate_cfo_compensation=True,
        activate_phase_compensation=True,
        ic_iterations=2,
        scorr_threshold_high=0.98,
        scorr_threshold_low=0.93,
        xcorr_threshold=30.0,
        num_network_interfaces=2,
        dst_id=42,
        src_id=0,
        mtu_size=84,
        cycle_interval=320.0e-6,
        timing_advance=280e-6,
        usrp_tx_addr="192.168.21.216",
        usrp_rx_addr="",
        usrp_tx_channels=[2, 3],
        usrp_rx_channels=[0, 1],
        carrier_freq=3.75e9,
        samp_rate=30.72e6,
        tx_gain=55.0,
        tx_digital_gain=2.7,
        rx_gain=55.0,
    ):
        noutputs = len(usrp_tx_channels) + len(usrp_rx_channels) * 4
        gr.hier_block2.__init__(
            self,
            "phy_layer",
            gr.io_signature(0, 0, 0),
            gr.io_signature(noutputs, noutputs, gr.sizeof_gr_complex),
        )
        self.message_port_register_hier_out("LLCout")
        self.message_port_register_hier_out("status")

        self.usrp_tx_channels = usrp_tx_channels
        self.usrp_rx_channels = usrp_rx_channels
        ##################################################
        # Variables
        ##################################################
        tx_packet_length_key = "packet_len"
        rx_packet_length_key = "rx_len"
        rx_packet_start_key = "frame_start"
        packet_header_overhead = 15
        byte_info_length = mtu_size + packet_header_overhead
        bit_info_length = 8 * byte_info_length

        constellation = digital.constellation_calcdist(
            [-0.707 - 0.707j, -0.707 + 0.707j, 0.707 + 0.707j, 0.707 - 0.707j],
            [0, 1, 3, 2],
            4,
            1,
            digital.constellation.AMPLITUDE_NORMALIZATION,
        ).base()
        constellation_order = constellation.bits_per_symbol()

        cyclic_shift_step = 2
        cyclic_shifts = list(
            range(0, len(usrp_tx_channels) * cyclic_shift_step, cyclic_shift_step)
        )
        self.conf = conf = get_gfdm_configuration(
            timeslots,
            subcarriers,
            active_subcarriers,
            overlap=2,
            # cp_len=subcarriers // 2,
            # cs_len=subcarriers // 4,
            cp_len=16,
            cs_len=8,
            filtertype="rrc",
            filteralpha=0.2,
            cyclic_shifts=cyclic_shifts,
        )
        self.code_conf = code_conf = polarwrap.get_polar_configuration(
            constellation_order * timeslots * active_subcarriers,
            bit_info_length,
            interleaver_type="convolutional",
        )

        ##################################################
        # USRP
        ##################################################
        tx_device_addr = parse_usrp_address(usrp_tx_addr)
        rx_device_addr = tx_device_addr
        if usrp_rx_addr:
            rx_device_addr = parse_usrp_address(usrp_rx_addr)
        if "addr" not in rx_device_addr:
            master_clock_rate = samp_rate
        else:
            master_clock_rate = "122.88e6"
        usrp_device_args = f"master_clock_rate={master_clock_rate},clock_source=gpsdo,time_source=gpsdo"

        self.uhd_usrp_source = uhd.usrp_source(
            ",".join((rx_device_addr, usrp_device_args)),
            uhd.stream_args(
                cpu_format="fc32",
                args="",
                channels=usrp_rx_channels,
            ),
        )
        self.uhd_usrp_source.set_clock_source("gpsdo", 0)
        self.uhd_usrp_source.set_time_source("gpsdo", 0)
        self.uhd_usrp_source.set_samp_rate(samp_rate)

        # see: https://files.ettus.com/manual/page_gpsdo_x3x0.html
        # https://kb.ettus.com/Synchronizing_USRP_Events_Using_Timed_Commands_in_UHD
        gps_locked = self.uhd_usrp_source.get_mboard_sensor("gps_locked", 0).to_bool()
        if gps_locked:
            print("Trying to align USRP time with host time...")
            last = self.uhd_usrp_source.get_time_last_pps()
            next = self.uhd_usrp_source.get_time_last_pps()
            while last == next:
                time.sleep(50e-3)
                last = next
                next = self.uhd_usrp_source.get_time_last_pps()
            time.sleep(200e-3)
            self.uhd_usrp_source.set_time_next_pps(
                uhd.time_spec(
                    self.uhd_usrp_source.get_mboard_sensor("gps_time").to_int() + 1
                )
            )
            # maybe a check would be in order?
        else:
            self.uhd_usrp_source.set_time_unknown_pps(uhd.time_spec(time.time()))

        for i in range(len(usrp_rx_channels)):
            self.uhd_usrp_source.set_center_freq(carrier_freq, i)
            self.uhd_usrp_source.set_antenna("RX2", i)
            self.uhd_usrp_source.set_gain(rx_gain, i)

        self.uhd_usrp_sink = uhd.usrp_sink(
            ",".join((rx_device_addr, usrp_device_args)),
            uhd.stream_args(
                cpu_format="fc32",
                args="",
                channels=usrp_tx_channels,
            ),
            tx_packet_length_key,
        )
        self.uhd_usrp_sink.set_clock_source("gpsdo", 0)
        self.uhd_usrp_sink.set_time_source("gpsdo", 0)
        self.uhd_usrp_sink.set_samp_rate(samp_rate)

        for i in range(len(usrp_tx_channels)):
            self.uhd_usrp_sink.set_center_freq(carrier_freq, i)
            self.uhd_usrp_sink.set_antenna("TX/RX", i)
            self.uhd_usrp_sink.set_gain(tx_gain, i)

        ##################################################
        # Network interfaces
        ##################################################
        self.tacmac_udp_interface = tacmac.udp_interface(
            src_id, dst_id, num_network_interfaces, mtu_size
        )
        self.tacmac_status_collector = tacmac.status_collector()

        self.tacmac_phy_transmitter = tacmac.phy_transmitter(
            conf.timeslots,
            conf.subcarriers,
            conf.active_subcarriers,
            conf.overlap,
            conf.subcarrier_map,
            conf.cp_len,
            conf.cs_len,
            conf.ramp_len,
            conf.tx_filter_taps,
            constellation_order,
            conf.window_taps,
            code_conf.frame_size,
            code_conf.frozen_bit_positions,
            code_conf.interleaver_indices,
            conf.pre_padding_len,
            conf.post_padding_len,
            conf.full_preambles,
            cycle_interval,
            timing_advance,
            tx_digital_gain,
            conf.cyclic_shifts,
            tx_packet_length_key,
        )
        self.tacmac_tags_to_msg_dict = tacmac.tags_to_msg_dict(gr.sizeof_gr_complex * 1)

        self.tacmac_lower_phy_receiver = tacmac.lower_phy_receiver(
            len(usrp_rx_channels),
            conf.timeslots,
            conf.subcarriers,
            conf.active_subcarriers,
            conf.overlap,
            conf.subcarrier_map,
            conf.cp_len,
            conf.cs_len,
            conf.ramp_len,
            conf.rx_filter_taps,
            constellation,
            ic_iterations,
            activate_phase_compensation,
            conf.core_preamble,
            scorr_threshold_high,
            scorr_threshold_low,
            xcorr_threshold,
            activate_cfo_compensation,
            rx_packet_start_key,
        )
        self.tacmac_periodic_time_tag_cc = tacmac.periodic_time_tag_cc(
            samp_rate, int(samp_rate // 10000)
        )

        ##################################################
        # Polar Decoder
        ##################################################
        list_size = 8
        crc_bits = 16
        decoder_type = "mixed"
        decoder_object = polarwrap.decoderwrap.make(
            code_conf.frame_size,
            list_size,
            code_conf.frozen_bit_positions,
            crc_bits,
            decoder_type,
        )

        self.symbolmapping_interleaver = symbolmapping.interleaver_ff(
            code_conf.interleaver_indices, True, False
        )
        self.fec_generic_decoder = fec.decoder(
            decoder_object, gr.sizeof_float, gr.sizeof_char
        )
        self.blocks_stream_to_tagged_stream = blocks.stream_to_tagged_stream(
            gr.sizeof_char, 1, byte_info_length, rx_packet_length_key
        )

        self.blocks_tagged_stream_to_pdu = blocks.tagged_stream_to_pdu(
            blocks.byte_t, rx_packet_length_key
        )

        ##################################################
        # Connections
        ##################################################
        for i in range(len(usrp_tx_channels)):
            self.connect((self.tacmac_phy_transmitter, i), (self.uhd_usrp_sink, i))
            self.connect((self.tacmac_phy_transmitter, i), (self, i))

        # Gather status info!
        self.connect(
            (self.tacmac_phy_transmitter, 0), (self.tacmac_tags_to_msg_dict, 0)
        )

        self.connect((self.uhd_usrp_source, 0), (self.tacmac_periodic_time_tag_cc, 0))
        for i in range(len(usrp_rx_channels)):
            self.connect((self.uhd_usrp_source, i), (self.tacmac_lower_phy_receiver, i))

        self.connect(
            (self.tacmac_lower_phy_receiver, 0),
            (self.symbolmapping_interleaver, 0),
            (self.fec_generic_decoder, 0),
            (self.blocks_stream_to_tagged_stream, 0),
            (self.blocks_tagged_stream_to_pdu, 0),
        )

        # corr, synced, estimate, symbol
        for i in range(len(usrp_rx_channels) * 4):
            self.connect(
                (self.tacmac_lower_phy_receiver, i + 1 + len(usrp_tx_channels)),
                (self, len(usrp_tx_channels) + i),
            )

        self.msg_connect((self.blocks_tagged_stream_to_pdu, "pdus"), (self, "LLCout"))
        self.msg_connect(
            (self.blocks_tagged_stream_to_pdu, "pdus"),
            (self.tacmac_udp_interface, "rx"),
        )
        self.msg_connect(
            (self.tacmac_periodic_time_tag_cc, "time_tag"),
            (self.tacmac_phy_transmitter, "time_tag"),
        )
        self.msg_connect(
            (self.tacmac_tags_to_msg_dict, "out"),
            (self.tacmac_status_collector, "in"),
        )
        self.msg_connect(
            (self.tacmac_udp_interface, "tx"), (self.tacmac_phy_transmitter, "pdus")
        )
        self.msg_connect(
            (self.tacmac_udp_interface, "timing"),
            (self.tacmac_phy_transmitter, "time_tag"),
        )
        self.msg_connect(
            (self.tacmac_udp_interface, "status"),
            (self.tacmac_status_collector, "in"),
        )
        self.msg_connect(
            (self.tacmac_status_collector, "out"),
            (self, "status"),
        )

    def get_activate_cfo_compensation(self):
        return self.tacmac_lower_phy_receiver.get_activate_cfo_compensation()

    def set_activate_cfo_compensation(self, activate_cfo_compensation):
        self.tacmac_lower_phy_receiver.set_activate_cfo_compensation(
            activate_cfo_compensation
        )

    def get_ic_iterations(self):
        return self.tacmac_lower_phy_receiver.get_ic_iterations()

    def set_ic_iterations(self, ic_iterations):
        self.tacmac_lower_phy_receiver.set_ic_iterations(ic_iterations)

    def get_activate_phase_compensation(self):
        return self.tacmac_lower_phy_receiver.get_activate_phase_compensation()

    def set_activate_phase_compensation(self, activate_phase_compensation):
        self.tacmac_lower_phy_receiver.set_activate_phase_compensation(
            activate_phase_compensation
        )

    def get_scorr_threshold_high(self):
        return self.tacmac_lower_phy_receiver.get_scorr_threshold_high()

    def set_scorr_threshold_high(self, scorr_threshold_high):
        self.tacmac_lower_phy_receiver.set_scorr_threshold_high(scorr_threshold_high)

    def get_scorr_threshold_low(self):
        return self.tacmac_lower_phy_receiver.get_scorr_threshold_low()

    def set_scorr_threshold_low(self, scorr_threshold_low):
        self.tacmac_lower_phy_receiver.set_scorr_threshold_low(scorr_threshold_low)

    def get_xcorr_threshold(self):
        return self.tacmac_lower_phy_receiver.get_xcorr_threshold()

    def set_xcorr_threshold(self, xcorr_threshold):
        self.tacmac_lower_phy_receiver.set_xcorr_threshold(xcorr_threshold)

    def get_tx_digital_gain(self):
        return self.tacmac_phy_transmitter.get_tx_digital_gain()

    def set_tx_digital_gain(self, tx_digital_gain):
        self.tacmac_phy_transmitter.set_tx_digital_gain(tx_digital_gain)

    def get_carrier_freq(self):
        return self.uhd_usrp_sink.get_center_freq()

    def set_carrier_freq(self, carrier_freq):
        for i in range(len(self.usrp_tx_channels)):
            self.uhd_usrp_sink.set_center_freq(carrier_freq, i)
        for i in range(len(self.usrp_rx_channels)):
            self.uhd_usrp_source.set_center_freq(carrier_freq, i)

    def get_rx_gain(self):
        return self.uhd_usrp_source.get_gain()

    def set_rx_gain(self, rx_gain):
        for i in range(len(self.usrp_rx_channels)):
            self.uhd_usrp_source.set_gain(rx_gain, i)

    def get_tx_gain(self):
        return self.uhd_usrp_sink.get_gain()

    def set_tx_gain(self, tx_gain):
        for i in range(len(self.usrp_tx_channels)):
            self.uhd_usrp_sink.set_gain(tx_gain, i)

    def get_cycle_interval(self):
        return self.tacmac_phy_transmitter.get_cycle_interval()

    def set_cycle_interval(self, cycle_interval):
        self.tacmac_phy_transmitter.set_cycle_interval(cycle_interval)

    def get_timing_advance(self):
        return self.tacmac_phy_transmitter.get_timing_advance()

    def set_timing_advance(self, timing_advance):
        self.tacmac_phy_transmitter.set_timing_advance(timing_advance)
