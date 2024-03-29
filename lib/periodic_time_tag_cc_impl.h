/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TACMAC_PERIODIC_TIME_TAG_CC_IMPL_H
#define INCLUDED_TACMAC_PERIODIC_TIME_TAG_CC_IMPL_H

#include <fmt/core.h>
#include <tacmac/periodic_time_tag_cc.h>

static const pmt::pmt_t TIME_KEY = pmt::string_to_symbol("rx_time");
static const pmt::pmt_t RATE_KEY = pmt::string_to_symbol("rx_rate");
static const pmt::pmt_t MSG_OUT_PORT = pmt::string_to_symbol("time_tag");

namespace gr {
namespace tacmac {

class periodic_time_tag_cc_impl : public periodic_time_tag_cc
{
private:
    const double d_samp_rate;
    const uint64_t d_tag_interval;

    uint64_t d_full_secs;
    double d_frac_secs;
    uint64_t d_tag_offset;
    uint64_t d_next_tag_offset;
    uint64_t d_slot_counter;

    uint64_t d_next_status_summary = 0;
    void log_status_summary();

    std::string get_formatted_tag_string(const uint64_t offset,
                                         const uint64_t full_secs,
                                         const double frac_secs) const
    {
        return fmt::format(
            "Tag: offset={}, time=({} - {:.7f})s", offset, full_secs, frac_secs);
    }

public:
    periodic_time_tag_cc_impl(double samp_rate, uint32_t tag_interval);
    ~periodic_time_tag_cc_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_PERIODIC_TIME_TAG_CC_IMPL_H */
