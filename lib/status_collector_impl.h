/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TACMAC_STATUS_COLLECTOR_IMPL_H
#define INCLUDED_TACMAC_STATUS_COLLECTOR_IMPL_H

#include "tacmac_utilities.h"
#include <tacmac/status_collector.h>

namespace gr {
namespace tacmac {

class status_collector_impl : public status_collector
{
private:
    const pmt::pmt_t d_in_port = pmt::mp("in");
    const pmt::pmt_t d_out_port = pmt::mp("out");

    uint64_t d_full_secs = 0;
    double d_frac_secs = 0.0;
    uint64_t d_time_ticks = 0;
    uint64_t d_tag_offset = 0;
    double d_samp_rate = 0.0;
    uint64_t d_slot_counter = 0;
    uint64_t d_burst_ack_counter = 0;

    uint64_t d_async_full_secs = 0;
    double d_async_frac_secs = 0.0;

    uint64_t d_tx_full_secs = 0;
    double d_tx_frac_secs = 0.0;

    const pmt::pmt_t UHD_ASYNC_MSG_KEY = pmt::string_to_symbol("uhd_async_msg");

    std::string get_formatted_time_spec(const uint64_t full_secs, const double frac_secs)
    {
        return std::string("(" + std::to_string(full_secs) + " . " +
                           std::to_string(frac_secs) + ")");
    }

    void handle_pdu_meta(const pmt::pmt_t& meta);
    void handle_uhd_tx(const pmt::pmt_t& msg);
    void handle_uhd_tx_async(const pmt::pmt_t& msg);

public:
    status_collector_impl();
    ~status_collector_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);

    void handle_msg(pmt::pmt_t pdu);
};

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_STATUS_COLLECTOR_IMPL_H */
