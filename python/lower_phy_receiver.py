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
            gr.io_signature(nport, nport, gr.sizeof_gr_complex),
            gr.io_signature.makev(1 + 5 * nport, 1 + 5 * nport, output_signature),
        )

        ##################################################
        # Variables
        ##################################################
        xcorr_compensate_frequency_offset = True
        constellation_type = "GRAY"
        cnr_tag_key = "cnr"  # still a "magic value"

        ##################################################
        # Synchronization
        ##################################################
        self.xfdm_sync_synchronizers = [
            xfdm_sync.sync_cc(
                preamble,
                scorr_threshold_high,
                scorr_threshold_low,
                xcorr_threshold,
                xcorr_compensate_frequency_offset,
                packet_length_key,
                antenna_port,
            )
            for antenna_port in range(nport)
        ]

        for port in range(nport):
            # Careful! First XCorr output then Synced output!
            self.connect(
                (self, port),
                (self.xfdm_sync_synchronizers[port], 0),
            )
            # The last connection is for optional for XCorr output!
            self.connect(
                (self.xfdm_sync_synchronizers[port], 1),
                (self, 1 + 1 * nport + port),
            )

        ##################################################
        # GFDM demodulation
        ##################################################
        self.gfdm_receivers = [
            gfdm.receiver_cc(
                timeslots,
                subcarriers,
                active_subcarriers,
                overlap,
                subcarrier_map,
                cp_len,
                cs_len,
                ramp_len,
                frequency_domain_taps,
                True,
                preamble,
                1,
                gfdm_constellation,
                ic_iterations,
                activate_phase_compensation,
                activate_cfo_compensation,
                packet_length_key,
                antenna_port,
            )
            for antenna_port in range(nport)
        ]

        for port in range(nport):
            # expose output symbols
            self.connect(
                (self.gfdm_receivers[port], 0),
                (self, 1 + 4 * nport + port),
            )
            # expose frame estimates
            self.connect((self.gfdm_receivers[port], 1), (self, 1 + 3 * nport + port))

        if nport < 2:
            for port in range(nport):
                # Careful! First XCorr output then Synced output!
                self.connect(
                    (self.xfdm_sync_synchronizers[port], 0),
                    (self, 1 + 2 * nport + port),
                )

                self.connect(
                    (self.xfdm_sync_synchronizers[port], 0),
                    (self.gfdm_receivers[port], 0),
                )
        else:
            # This is probably the only block we only have once. Everything else SCALES!
            self.xfdm_sync_sync_tag_align_cc = xfdm_sync.sync_tag_align_cc(
                nport, packet_length_key
            )

            for port in range(nport):
                # Careful! First XCorr output then Synced output!
                self.connect(
                    (self.xfdm_sync_synchronizers[port], 0),
                    (self.xfdm_sync_sync_tag_align_cc, port),
                    (self, 1 + 2 * nport + port),
                )
                self.connect(
                    (self.xfdm_sync_sync_tag_align_cc, port),
                    (self.gfdm_receivers[port], 0),
                )

        ##################################################
        # Symboldemapping
        ##################################################
        self.symbolmapping_symbol_demappers = [
            symbolmapping.symbol_demapper_cf(
                gfdm_constellation.bits_per_symbol(),
                constellation_type,
                f"{cnr_tag_key}{antenna_port}",
            )
            for antenna_port in range(nport)
        ]

        for port in range(nport):
            self.connect(
                (self.gfdm_receivers[port], 0),
                (self.symbolmapping_symbol_demappers[port], 0),
            )

            self.connect(
                (self.symbolmapping_symbol_demappers[port], 0),
                (self, 1 + 0 * nport + port),
            )

        if nport < 2:
            self.connect(
                (self.symbolmapping_symbol_demappers[0], 0),
                (self, 0),
            )
        else:
            # Sum up all those pretty LLRs!
            self.blocks_add_xx = blocks.add_vff(1)

            for port in range(nport):
                self.connect(
                    (self.symbolmapping_symbol_demappers[port], 0),
                    (self.blocks_add_xx, port),
                )

            # The only required port! The combined LLR output.
            self.connect((self.blocks_add_xx, 0), (self, 0))

        ##################################################
        # Connections
        ##################################################

        # Sorted in groups for now...

    def get_activate_cfo_compensation(self):
        return self.gfdm_receivers[0].get_activate_cfo_compensation()

    def set_activate_cfo_compensation(self, activate_cfo_compensation):
        for receiver in self.gfdm_receivers:
            receiver.set_activate_cfo_compensation(activate_cfo_compensation)

    def get_ic_iterations(self):
        return self.gfdm_receivers[0].get_ic_iterations()

    def set_ic_iterations(self, ic_iterations):
        for receiver in self.gfdm_receivers:
            receiver.set_ic_iterations(ic_iterations)

    def get_activate_phase_compensation(self):
        return self.gfdm_receivers[0].get_activate_phase_compensation()

    def set_activate_phase_compensation(self, activate_phase_compensation):
        for receiver in self.gfdm_receivers:
            receiver.set_activate_phase_compensation(activate_phase_compensation)

    def get_scorr_threshold_high(self):
        return self.xfdm_sync_synchronizers[0].get_scorr_threshold_high()

    def set_scorr_threshold_high(self, scorr_threshold_high):
        for t in self.xfdm_sync_synchronizers:
            t.set_scorr_threshold_high(scorr_threshold_high)

    def get_scorr_threshold_low(self):
        return self.xfdm_sync_synchronizers[0].get_scorr_threshold_low()

    def set_scorr_threshold_low(self, scorr_threshold_low):
        for t in self.xfdm_sync_synchronizers:
            t.set_scorr_threshold_low(scorr_threshold_low)

    def get_xcorr_threshold(self):
        return self.xfdm_sync_synchronizers[0].get_xcorr_threshold()

    def set_xcorr_threshold(self, xcorr_threshold):
        for x in self.xfdm_sync_synchronizers:
            x.set_xcorr_threshold(xcorr_threshold)
