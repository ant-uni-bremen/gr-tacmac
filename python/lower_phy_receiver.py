#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2021 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

from gnuradio import blocks
from gnuradio import gr
from gnuradio import digital

import gfdm
import symbolmapping
import xfdm_sync


class lower_phy_receiver(gr.hier_block2):
    """
    docstring for block lower_phy_receiver
    """

    def __init__(
        self,
        nport=2,
        timeslots=15,
        subcarriers=64,
        active_subcarriers=60,
        overlap=2,
        subcarrier_map=list(range(60)),
        cp_len=16,
        cs_len=8,
        ramp_len=8,
        frequency_domain_taps=list(range(30)),
        gfdm_constellation=digital.constellation_qpsk().base(),
        ic_iterations=2,
        activate_phase_compensation=True,
        preamble=[1.0 + 1.0j] * 128,
        scorr_threshold_high=0.98,
        scorr_threshold_low=0.93,
        xcorr_threshold=30.0,
        activate_cfo_compensation=True,
        packet_length_key="packet_len",
    ):
        output_signature = [gr.sizeof_float,] * (1 + nport) + [
            gr.sizeof_gr_complex,
        ] * 4 * nport
        gr.hier_block2.__init__(
            self,
            "lower_phy_receiver",
            gr.io_signature(nport, nport, gr.sizeof_gr_complex),  # Input signature
            gr.io_signature.makev(1 + 5 * nport, 1 + 5 * nport, output_signature),
        )  # Output signature

        ##################################################
        # Parameters
        ##################################################
        self.activate_cfo_compensation = activate_cfo_compensation
        self.active_subcarriers = active_subcarriers
        self.cp_len = cp_len
        self.cs_len = cs_len
        self.frequency_domain_taps = frequency_domain_taps
        self.gfdm_constellation = gfdm_constellation
        self.ic_iterations = ic_iterations
        self.overlap = overlap
        self.activate_phase_compensation = activate_phase_compensation
        self.preamble = preamble
        self.ramp_len = ramp_len
        self.scorr_threshold_high = scorr_threshold_high
        self.scorr_threshold_low = scorr_threshold_low
        self.subcarrier_map = subcarrier_map
        self.subcarriers = subcarriers
        self.packet_length_key = packet_length_key
        self.timeslots = timeslots
        self.xcorr_threshold = xcorr_threshold

        ##################################################
        # Variables
        ##################################################
        self.frame_len = frame_len = (
            timeslots * subcarriers + 2 * cp_len + 2 * cs_len + 2 * subcarriers
        )
        self.block_len = block_len = timeslots * subcarriers
        self.normalize_scorr = normalize_scorr = True
        self.preamble_len = preamble_len = len(preamble)
        self.full_preamble_len = full_preamble_len = cp_len + preamble_len + cs_len
        self.scorr_delay = scorr_delay = preamble_len // 2
        self.xcorr_compensate_frequency_offset = (
            xcorr_compensate_frequency_offset
        ) = True
        self.foo = "bar"
        self.block_len = block_len = timeslots * subcarriers
        self.channel_estimator_id = channel_estimator_id = 1
        self.sc_map_is_dc_free = sc_map_is_dc_free = True
        self.gfdm_resources_per_timeslot = gfdm_resources_per_timeslot = True
        self.constellation_type = constellation_type = "GRAY"
        self.cnr_tag_key = cnr_tag_key = "cnr"  # still a "magic value"

        ##################################################
        # Synchronization
        ##################################################
        self.xfdm_sync_sc_delay_corrs = [
            xfdm_sync.sc_delay_corr(scorr_delay, normalize_scorr) for _ in range(nport)
        ]
        self.xfdm_sync_sc_taggers = [
            xfdm_sync.sc_tagger(
                scorr_threshold_low,
                scorr_threshold_high,
                scorr_delay,
                packet_length_key,
            )
            for _ in range(nport)
        ]

        self.xfdm_sync_xcorr_taggers = [
            xfdm_sync.xcorr_tagger(
                xcorr_threshold,
                preamble,
                xcorr_compensate_frequency_offset,
                packet_length_key,
            )
            for _ in range(nport)
        ]

        # This is probably the only block we only have once. Everything else SCALES!
        self.xfdm_sync_sync_tag_align_cc = xfdm_sync.sync_tag_align_cc(
            nport, packet_length_key
        )

        for port in range(nport):
            # Careful! First XCorr output then Synced output!
            self.connect(
                (self, port),
                (self.xfdm_sync_sc_delay_corrs[port], 0),
                (self.xfdm_sync_sc_taggers[port], 0),
                (self.xfdm_sync_xcorr_taggers[port], 0),
                (self.xfdm_sync_sync_tag_align_cc, port),
                (self, 1 + 2 * nport + port),
            )
            # The last connection is for optional for XCorr output!
            self.connect(
                (self.xfdm_sync_sc_delay_corrs[port], 1),
                (self.xfdm_sync_sc_taggers[port], 1),
                (self.xfdm_sync_xcorr_taggers[port], 1),
                (self, 1 + 1 * nport + port),
            )

        ##################################################
        # GFDM demodulation
        ##################################################
        self.gfdm_extract_bursts = [
            gfdm.extract_burst_cc(
                frame_len, cp_len, packet_length_key, activate_cfo_compensation
            )
            for _ in range(nport)
        ]

        self.gfdm_remove_prefix_datas = [
            gfdm.remove_prefix_cc(
                frame_len, block_len, full_preamble_len + cp_len, packet_length_key
            )
            for _ in range(nport)
        ]

        self.gfdm_remove_prefix_preambles = [
            gfdm.remove_prefix_cc(frame_len, preamble_len, cp_len, packet_length_key)
            for _ in range(nport)
        ]

        self.gfdm_channel_estimators = [
            gfdm.channel_estimator_cc(
                timeslots,
                subcarriers,
                active_subcarriers,
                sc_map_is_dc_free,
                channel_estimator_id,
                preamble,
            )
            for _ in range(nport)
        ]

        self.gfdm_advanced_receivers = [
            gfdm.advanced_receiver_sb_cc(
                timeslots,
                subcarriers,
                overlap,
                ic_iterations,
                frequency_domain_taps,
                gfdm_constellation,
                subcarrier_map,
                activate_phase_compensation,
            )
            for _ in range(nport)
        ]

        self.gfdm_resource_demappers = [
            gfdm.resource_demapper_cc(
                timeslots,
                subcarriers,
                active_subcarriers,
                subcarrier_map,
                gfdm_resources_per_timeslot,
            )
            for _ in range(nport)
        ]

        for port in range(nport):
            self.connect(
                (self.xfdm_sync_sync_tag_align_cc, port),
                (self.gfdm_extract_bursts[port], 0),
                (self.gfdm_remove_prefix_datas[port], 0),
                (self.gfdm_advanced_receivers[port], 0),
                (self.gfdm_resource_demappers[port], 0),
            )
            self.connect(
                (self.gfdm_extract_bursts[port], 0),
                (self.gfdm_remove_prefix_preambles[port], 0),
                (self.gfdm_channel_estimators[port], 0),
                (self.gfdm_advanced_receivers[port], 1),
            )

            self.connect(
                (self.gfdm_channel_estimators[port], 0), (self, 1 + 3 * nport + port)
            )
            self.connect(
                (self.gfdm_resource_demappers[port], 0), (self, 1 + 4 * nport + port)
            )

        ##################################################
        # Symboldemapping
        ##################################################
        self.symbolmapping_symbol_demappers = [
            symbolmapping.symbol_demapper_cf(
                gfdm_constellation.bits_per_symbol(), constellation_type, cnr_tag_key
            )
            for _ in range(nport)
        ]

        # Sum up all those pretty LLRs!
        self.blocks_add_xx = blocks.add_vff(1)

        for port in range(nport):
            self.connect(
                (self.gfdm_resource_demappers[port], 0),
                (self.symbolmapping_symbol_demappers[port], 0),
                (self.blocks_add_xx, port),
            )

            self.connect(
                (self.symbolmapping_symbol_demappers[port], 0),
                (self, 1 + 0 * nport + port),
            )

        # The only required port! The combined LLR output.
        self.connect((self.blocks_add_xx, 0), (self, 0))

        ##################################################
        # Connections
        ##################################################

        # Sorted in groups for now...

    def get_activate_cfo_compensation(self):
        return self.activate_cfo_compensation

    def set_activate_cfo_compensation(self, activate_cfo_compensation):
        self.activate_cfo_compensation = activate_cfo_compensation
        for extractor in self.gfdm_extract_bursts:
            extractor.activate_cfo_compensation(activate_cfo_compensation)

    def get_ic_iterations(self):
        return self.ic_iterations

    def set_ic_iterations(self, ic_iterations):
        self.ic_iterations = ic_iterations
        for demodulator in self.gfdm_advanced_receivers:
            demodulator.set_ic_iterations(ic_iterations)

    def get_activate_phase_compensation(self):
        return self.activate_phase_compensation

    def set_activate_phase_compensation(self, activate_phase_compensation):
        self.activate_phase_compensation = activate_phase_compensation
        for demodulator in self.gfdm_advanced_receivers:
            demodulator.set_phase_compensation(activate_phase_compensation)

    def get_scorr_threshold_high(self):
        return self.scorr_threshold_high

    def set_scorr_threshold_high(self, scorr_threshold_high):
        self.scorr_threshold_high = scorr_threshold_high
        for t in self.xfdm_sync_sc_taggers:
            t.set_threshold_high(scorr_threshold_high)

    def get_scorr_threshold_low(self):
        return self.scorr_threshold_low

    def set_scorr_threshold_low(self, scorr_threshold_low):
        self.scorr_threshold_low = scorr_threshold_low
        for t in self.xfdm_sync_sc_taggers:
            t.set_threshold_low(scorr_threshold_low)

    def get_xcorr_threshold(self):
        return self.xcorr_threshold

    def set_xcorr_threshold(self, xcorr_threshold):
        self.xcorr_threshold = xcorr_threshold
        for x in self.xfdm_sync_xcorr_taggers:
            x.set_threshold(xcorr_threshold)
