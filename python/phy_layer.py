#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import pathlib
import datetime
import time
import numpy as np
from pprint import pprint, pformat
from gnuradio import gr
from gnuradio import uhd
from gnuradio import digital
from gnuradio import blocks
from gnuradio import fec
import tacmac
import polarwrap
import symbolmapping
from gfdm.pygfdm import get_gfdm_configuration


def parse_usrp_address(addr: str):
    uhd_keywords = ["serial", "addr", "resource", "name", "type", "vid", "pid"]
    for k in uhd_keywords:
        # we expect plain IP addresses. Otherwise, prefer user input.
        if k in addr:
            return addr
    return ",".join(
        [f"addr{i}={a}" for i, a in enumerate(addr.replace(",", " ").split())]
    )


def get_usrp_device_args_string(master_clock_rate, clock_source, time_source):
    return f"master_clock_rate={master_clock_rate},clock_source={clock_source},time_source={time_source}"


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
        usrp_tx_addr="",
        usrp_rx_addr="",
        usrp_tx_channels=[2, 3],
        usrp_rx_channels=[0, 1],
        carrier_freq=3.75e9,
        samp_rate=30.72e6,
        tx_gain=55.0,
        tx_digital_gain=2.7,
        rx_gain=55.0,
        master_clock_rate=122.88e6,
        save_rx_samples_to_file=False,
        use_timed_commands=True,
    ):
        noutputs = len(usrp_tx_channels) + len(usrp_rx_channels) * 4
        gr.hier_block2.__init__(
            self,
            "phy_layer",
            gr.io_signature(0, 0, 0),
            gr.io_signature(noutputs, noutputs, gr.sizeof_gr_complex),
        )
        self.logger = gr.logger(f"gr_log.{self.symbol_name()}")
        self.message_port_register_hier_out("LLCout")
        self.message_port_register_hier_out("status")

        self.usrp_tx_channels = usrp_tx_channels
        self.usrp_rx_channels = usrp_rx_channels
        ##################################################
        # Variables
        ##################################################
        tx_packet_length_key = "packet_len"
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

        cs_len = 8
        cp_len = 2 * cs_len
        if cp_len >= subcarriers:
            cp_len = subcarriers // 2
            cs_len = cp_len // 2

        conf = get_gfdm_configuration(
            timeslots,
            subcarriers,
            active_subcarriers,
            overlap=2,
            cp_len=cp_len,
            cs_len=cs_len,
            filtertype="rrc",
            filteralpha=0.2,
            cyclic_shifts=cyclic_shifts,
        )

        print_dict = {}
        for k, v in conf._asdict().items():
            if isinstance(v, int):
                print_dict[k] = v
        self.logger.debug("GFDM configuration\n" + pformat(print_dict))

        code_conf = polarwrap.get_polar_configuration(
            constellation_order * timeslots * active_subcarriers,
            bit_info_length,
            interleaver_type="convolutional",
        )

        print_dict = {}
        for k, v in code_conf._asdict().items():
            if isinstance(v, int):
                print_dict[k] = v
        self.logger.debug("FEC configuration\n" + pformat(print_dict))

        ##################################################
        # USRP
        ##################################################
        self.uhd_usrp_source, self.uhd_usrp_sink = self.initialize_usrps(
            usrp_tx_addr,
            usrp_rx_addr,
            usrp_tx_channels,
            usrp_rx_channels,
            master_clock_rate,
            samp_rate,
            carrier_freq,
            tx_gain,
            rx_gain,
            tx_packet_length_key,
        )

        if save_rx_samples_to_file:
            self.logger.info("Save RX samples to files ...")
            file_suffix = "cdat"
            timestring = str(datetime.datetime.now()).replace(" ", "-")
            rx_info = self.uhd_usrp_source.get_usrp_info()
            usrpstring = f"{rx_info['mboard_id']}-n310-{rx_info['rx_antenna']}"
            folder = pathlib.Path.cwd().absolute()
            cfostring = f"{int(activate_cfo_compensation)}"
            self.rx_samples_file_sinks = []
            for i in range(len(usrp_rx_channels)):
                rxfilename = f"{folder}/{usrpstring}-{i}_CFO-{cfostring}_{timestring}.{file_suffix}"
                self.logger.info(f"port={i} -> {rxfilename}")
                self.rx_samples_file_sinks.append(
                    blocks.file_sink(
                        gr.sizeof_gr_complex,
                        rxfilename,
                        False,
                    )
                )
                self.rx_samples_file_sinks[i].set_unbuffered(False)
                self.connect(
                    (self.uhd_usrp_source, i), (self.rx_samples_file_sinks[i], 0)
                )

        tx_info = self.uhd_usrp_sink.get_usrp_info()
        usrp_type = "n3xx"
        if "B2" in tx_info["mboard_id"]:
            usrp_type = "b200"

        ##################################################
        # Network interfaces
        ##################################################
        self.tacmac_udp_interface = tacmac.udp_interface(
            src_id, dst_id, num_network_interfaces, mtu_size
        )
        self.tacmac_status_collector = tacmac.status_collector()

        more_padding = 0
        if usrp_type == "b200":
            buffer_max = 4096  # This is the "short frame" hard limit!
            possible_padding = max(buffer_max - conf.padded_frame_len, 0)
            more_padding = min(possible_padding, 1024)
        self.logger.debug(
            f"{usrp_type=}, {conf.pre_padding_len=}, {more_padding=}, {conf.post_padding_len=}"
        )

        enable_tx_latency_reporting = False
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
            conf.pre_padding_len + more_padding,
            conf.post_padding_len,
            conf.full_preambles,
            cycle_interval,
            timing_advance,
            tx_digital_gain,
            conf.cyclic_shifts,
            tx_packet_length_key,
            use_timed_commands,
            enable_tx_latency_reporting,
        )
        self.tacmac_tags_to_msg_dict = tacmac.tags_to_msg_dict(gr.sizeof_gr_complex * 1)

        self.logger.debug(
            f"{activate_cfo_compensation=}, {activate_phase_compensation=}"
        )
        self.tacmac_phy_receiver = tacmac.phy_receiver(
            len(usrp_rx_channels),
            conf.timeslots,
            conf.subcarriers,
            conf.active_subcarriers,
            code_conf.info_size,
            activate_cfo_compensation,
            activate_phase_compensation,
            ic_iterations,
            scorr_threshold_high,
            scorr_threshold_low,
            xcorr_threshold,
        )

        self.tacmac_periodic_time_tag_cc = tacmac.periodic_time_tag_cc(
            samp_rate, int(samp_rate // 10000)
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
            self.connect((self.uhd_usrp_source, i), (self.tacmac_phy_receiver, i))

        # self.tag_dbg = blocks.tag_debug(gr.sizeof_gr_complex, "tx_latency", "dsp_latency")
        # self.connect((self.tacmac_phy_transmitter, 0), (self.tag_dbg, 0))
        # self.tag_dbg = blocks.tag_debug(gr.sizeof_gr_complex, "", "")
        # self.connect((self.tacmac_phy_receiver, 3 * 2), (self.tag_dbg, 0))

        nstreams = len(usrp_rx_channels)
        for i in range(nstreams):
            # correlation values
            self.connect((self.tacmac_phy_receiver, nstreams + i), (self, nstreams + i))
            # RX stream with sync tags
            self.connect((self.tacmac_phy_receiver, i), (self, 2 * nstreams + i))
            # channel estimates
            self.connect(
                (self.tacmac_phy_receiver, 3 * nstreams + i), (self, 3 * nstreams + i)
            )
            # received symbols
            self.connect(
                (self.tacmac_phy_receiver, 4 * nstreams + i), (self, 4 * nstreams + i)
            )

        self.msg_connect((self.tacmac_phy_receiver, "pdus"), (self, "LLCout"))
        self.msg_connect(
            (self.tacmac_phy_receiver, "pdus"),
            (self.tacmac_udp_interface, "rx"),
        )

        # self.msg_dbg = blocks.message_debug()
        # self.msg_connect(
        #     (self.tacmac_phy_receiver, "pdus"),
        #     (self.msg_dbg, "print"),
        # )

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

        # self.msg_connect(
        #     (self.uhd_usrp_sink, "async_msgs"),
        #     (self.tacmac_status_collector, "in"),
        # )

    def initialize_usrp_source(
        self,
        rx_device_addr,
        usrp_device_args,
        usrp_rx_channels,
        rx_gain,
        carrier_freq,
        samp_rate,
    ):
        self.logger.info("Creating USRP source ...")
        uhd_usrp_source = uhd.usrp_source(
            ",".join((rx_device_addr, usrp_device_args)),
            uhd.stream_args(
                cpu_format="fc32",
                args="",
                channels=usrp_rx_channels,
            ),
        )
        self.logger.info("Configuring USRP source clocks ...")
        if "B2" in uhd_usrp_source.get_usrp_info()["mboard_id"]:
            self.logger.debug("Detected USRP B210, using GPSDO clock source ...")
            uhd_usrp_source.set_clock_source("gpsdo", 0)
            uhd_usrp_source.set_time_source("gpsdo", 0)
        uhd_usrp_source.set_samp_rate(samp_rate)

        self.logger.info("Configuring USRP source RF ...")
        for i in range(len(usrp_rx_channels)):
            uhd_usrp_source.set_center_freq(carrier_freq, i)
            uhd_usrp_source.set_antenna("RX2", i)
            uhd_usrp_source.set_gain(rx_gain, i)

        return uhd_usrp_source

    def initialize_usrp_sink(
        self,
        tx_device_addr,
        usrp_device_args,
        usrp_tx_channels,
        tx_gain,
        carrier_freq,
        samp_rate,
        tx_packet_length_key,
    ):
        self.logger.info("Creating USRP sink ...")
        uhd_usrp_sink = uhd.usrp_sink(
            ",".join((tx_device_addr, usrp_device_args)),
            uhd.stream_args(
                cpu_format="fc32",
                args="",
                channels=usrp_tx_channels,
            ),
            tx_packet_length_key,
        )
        self.logger.info("Configuring USRP sink clocks ...")
        if "B2" in uhd_usrp_sink.get_usrp_info()["mboard_id"]:
            self.logger.debug("Detected USRP B210, using GPSDO clock source ...")
            uhd_usrp_sink.set_clock_source("gpsdo", 0)
            uhd_usrp_sink.set_time_source("gpsdo", 0)
        uhd_usrp_sink.set_samp_rate(samp_rate)

        uhd_sink_buffer_size = 2048 * 2
        # uhd_sink_buffer_size = 3072 * 2
        uhd_usrp_sink.set_min_output_buffer(uhd_sink_buffer_size)
        uhd_usrp_sink.set_max_output_buffer(uhd_sink_buffer_size)

        self.logger.info("Configuring USRP sink RF ...")
        for i in range(len(usrp_tx_channels)):
            uhd_usrp_sink.set_center_freq(carrier_freq, i)
            uhd_usrp_sink.set_antenna("TX/RX", i)
            uhd_usrp_sink.set_gain(tx_gain, i)
            uhd_usrp_sink.set_bandwidth(samp_rate, i)
        return uhd_usrp_sink

    def initialize_usrps(
        self,
        usrp_tx_addr,
        usrp_rx_addr,
        usrp_tx_channels,
        usrp_rx_channels,
        master_clock_rate,
        samp_rate,
        carrier_freq,
        tx_gain,
        rx_gain,
        tx_packet_length_key,
    ):
        ##################################################
        # USRP
        ##################################################
        if len(usrp_tx_addr) == 0:
            device = tacmac.uhd_configuration.get_device()
            usrp_tx_addr = parse_usrp_address(device["addr"])
        tx_device_addr = parse_usrp_address(usrp_tx_addr)
        rx_device_addr = tx_device_addr
        if usrp_rx_addr:
            rx_device_addr = parse_usrp_address(usrp_rx_addr)

        # if "addr" not in rx_device_addr:
        #     master_clock_rate = samp_rate
        is_multi_usrp_config = "addr0" in rx_device_addr and "addr1" in rx_device_addr
        self.logger.info(f"Detected multiple USRP config: {is_multi_usrp_config}")
        self.logger.debug(f"USRP TX address: {tx_device_addr}")
        self.logger.debug(f"USRP RX address: {rx_device_addr}")

        master_clock_rate = str(master_clock_rate)
        usrp_clock_source = "internal"
        usrp_time_source = "internal"
        if is_multi_usrp_config:
            usrp_clock_source = "external"
            usrp_time_source = "external"

        usrp_device_args = get_usrp_device_args_string(
            master_clock_rate, usrp_clock_source, usrp_time_source
        )

        self.logger.debug(f"{usrp_device_args=}")

        uhd_usrp_source = self.initialize_usrp_source(
            rx_device_addr,
            usrp_device_args,
            usrp_rx_channels,
            rx_gain,
            carrier_freq,
            samp_rate,
        )

        # see: https://files.ettus.com/manual/page_gpsdo_x3x0.html
        # https://kb.ettus.com/Synchronizing_USRP_Events_Using_Timed_Commands_in_UHD
        gps_locked = uhd_usrp_source.get_mboard_sensor("gps_locked", 0).to_bool()
        if gps_locked:
            self.logger.info("Configuring USRP with GPSDO ...")
            usrp_clock_source = "gpsdo"
            usrp_time_source = "gpsdo"
            uhd_usrp_source.set_clock_source(usrp_clock_source)
            uhd_usrp_source.set_time_source(usrp_time_source)
            usrp_device_args = get_usrp_device_args_string(
                master_clock_rate, usrp_clock_source, usrp_time_source
            )
            self.logger.debug("Trying to align USRP time with host time...")
            last = uhd_usrp_source.get_time_last_pps()
            next = uhd_usrp_source.get_time_last_pps()
            while last == next:
                time.sleep(50e-3)
                last = next
                next = uhd_usrp_source.get_time_last_pps()
            time.sleep(200e-3)
            uhd_usrp_source.set_time_next_pps(
                uhd.time_spec(
                    uhd_usrp_source.get_mboard_sensor("gps_time").to_int() + 1
                )
            )
            # maybe a check would be in order?
        elif is_multi_usrp_config:
            self.logger.debug(
                "Multi USRP config with external clock: using system time next PPS ..."
            )
            uhd_usrp_source.set_time_next_pps(uhd.time_spec(np.ceil(time.time())))

        else:
            self.logger.debug("USRP.GPS not available: using system time...")
            uhd_usrp_source.set_time_now(uhd.time_spec(time.time()), uhd.ALL_MBOARDS)

        uhd_usrp_sink = self.initialize_usrp_sink(
            tx_device_addr,
            usrp_device_args,
            usrp_tx_channels,
            tx_gain,
            carrier_freq,
            samp_rate,
            tx_packet_length_key,
        )

        tx_info = uhd_usrp_sink.get_usrp_info()
        rx_info = uhd_usrp_source.get_usrp_info()
        self.log_usrp_info(tx_info, rx_info, usrp_tx_channels, usrp_rx_channels)

        return uhd_usrp_source, uhd_usrp_sink

    def log_usrp_info(self, tx_info, rx_info, usrp_tx_channels, usrp_rx_channels):
        # a bit of device info digging
        common_keys = sorted(list(set(rx_info.keys()) & set(tx_info.keys())))
        tx_keys = sorted(list(set(tx_info.keys()) - set(rx_info.keys())))
        rx_keys = sorted(list(set(rx_info.keys()) - set(tx_info.keys())))
        self.logger.debug(
            f"USRP channels: TX={usrp_tx_channels}\tRX={usrp_rx_channels}"
        )
        self.logger.debug(f"UHD version: {uhd.get_version_string()}")
        usrp_common = "\n".join(
            [f"{k:16}{tx_info[k]:20}{rx_info[k]}" for k in common_keys]
        )
        self.logger.debug(f"USRP common config\n{usrp_common}")
        usrp_tx_info = "\n".join([f"{k:16}{tx_info[k]}" for k in tx_keys])
        self.logger.debug(f"USRP TX config\n{usrp_tx_info}")

        usrp_rx_info = "\n".join([f"{k:16}{rx_info[k]}" for k in rx_keys])
        self.logger.debug(f"USRP RX config\n{usrp_rx_info}")

    def get_activate_cfo_compensation(self):
        return self.tacmac_phy_receiver.get_activate_cfo_compensation()

    def set_activate_cfo_compensation(self, activate_cfo_compensation):
        self.tacmac_phy_receiver.set_activate_cfo_compensation(
            activate_cfo_compensation
        )

    def get_ic_iterations(self):
        return self.tacmac_phy_receiver.get_ic_iterations()

    def set_ic_iterations(self, ic_iterations):
        self.tacmac_phy_receiver.set_ic_iterations(ic_iterations)

    def get_activate_phase_compensation(self):
        return self.tacmac_phy_receiver.get_activate_phase_compensation()

    def set_activate_phase_compensation(self, activate_phase_compensation):
        self.tacmac_phy_receiver.set_activate_phase_compensation(
            activate_phase_compensation
        )

    def get_scorr_threshold_high(self):
        return self.tacmac_phy_receiver.get_scorr_threshold_high()

    def set_scorr_threshold_high(self, scorr_threshold_high):
        self.tacmac_phy_receiver.set_scorr_threshold_high(scorr_threshold_high)

    def get_scorr_threshold_low(self):
        return self.tacmac_phy_receiver.get_scorr_threshold_low()

    def set_scorr_threshold_low(self, scorr_threshold_low):
        self.tacmac_phy_receiver.set_scorr_threshold_low(scorr_threshold_low)

    def get_xcorr_threshold(self):
        return self.tacmac_phy_receiver.get_xcorr_threshold()

    def set_xcorr_threshold(self, xcorr_threshold):
        self.tacmac_phy_receiver.set_xcorr_threshold(xcorr_threshold)

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
