/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "periodic_time_tag_cc_impl.h"
#include <gnuradio/io_signature.h>
#include <fmt/core.h>

namespace gr {
namespace tacmac {

periodic_time_tag_cc::sptr periodic_time_tag_cc::make(double samp_rate,
                                                      uint32_t tag_interval)
{
    return gnuradio::get_initial_sptr(
        new periodic_time_tag_cc_impl(samp_rate, tag_interval));
}


/*
 * The private constructor
 */
periodic_time_tag_cc_impl::periodic_time_tag_cc_impl(double samp_rate,
                                                     uint32_t tag_interval)
    : gr::sync_block("periodic_time_tag_cc",
                     gr::io_signature::make(1, 1, sizeof(gr_complex)),
                     gr::io_signature::make(0, 1, sizeof(gr_complex))),
      d_samp_rate(samp_rate),
      d_tag_interval(tag_interval),
      d_full_secs(0),
      d_frac_secs(0.0),
      d_tag_offset(0),
      d_next_tag_offset(tag_interval),
      d_slot_counter(0)
{
    message_port_register_out(MSG_OUT_PORT);
}

/*
 * Our virtual destructor.
 */
periodic_time_tag_cc_impl::~periodic_time_tag_cc_impl() {}

void periodic_time_tag_cc_impl::log_status_summary()
{
    if (d_next_status_summary > d_tag_offset) {
        return;
    }

    GR_LOG_DEBUG(
        d_logger,
        fmt::format("STATUS: {}, counter={}",
                    get_formatted_tag_string(d_tag_offset, d_full_secs, d_frac_secs),
                    d_slot_counter));
    d_next_status_summary += uint64_t(2 * d_samp_rate);
}

int periodic_time_tag_cc_impl::work(int noutput_items,
                                    gr_vector_const_void_star& input_items,
                                    gr_vector_void_star& output_items)
{
    const gr_complex* in = (const gr_complex*)input_items[0];
    if (output_items.size() > 0) {
        gr_complex* out = (gr_complex*)output_items[0];
        memcpy(out, in, sizeof(gr_complex) * noutput_items);
    }

    std::vector<tag_t> tags;
    get_tags_in_range(
        tags, 0, nitems_read(0), (nitems_read(0) + noutput_items), RATE_KEY);
    for (auto t : tags) {
        double tag_rate = pmt::to_double(t.value);
        if (std::fabs(tag_rate - d_samp_rate) > 1.0e-1) {
            std::string err_msg = fmt::format(
                "Runtime rate change not supported! configured={}MSps, received={}MSps",
                d_samp_rate / 1.0e6,
                tag_rate / 1.0e6);

            GR_LOG_ERROR(this->d_logger, err_msg);
            throw std::runtime_error(err_msg);
        }
    }

    get_tags_in_range(
        tags, 0, nitems_read(0), (nitems_read(0) + noutput_items), TIME_KEY);
    for (auto t : tags) {
        d_tag_offset = t.offset;
        d_full_secs = pmt::to_uint64(pmt::tuple_ref(t.value, 0));
        d_frac_secs = pmt::to_double(pmt::tuple_ref(t.value, 1));
        d_next_tag_offset = t.offset; // + d_tag_interval;
        GR_LOG_DEBUG(this->d_logger,
                     "Received new tag @offset=" + get_formatted_tag_string(d_tag_offset,
                                                                            d_full_secs,
                                                                            d_frac_secs));
    }

    uint64_t total_items = nitems_read(0) + noutput_items;
    while (total_items > d_next_tag_offset) {
        d_frac_secs += (d_next_tag_offset - d_tag_offset) / d_samp_rate;
        if (d_frac_secs >= 1.0) {
            d_full_secs += 1;
            d_frac_secs -= 1.0;
        }
        pmt::pmt_t info = pmt::make_tuple(pmt::from_uint64(d_full_secs),
                                          pmt::from_double(d_frac_secs),
                                          pmt::from_uint64(d_next_tag_offset),
                                          pmt::from_double(d_samp_rate),
                                          pmt::from_uint64(d_slot_counter));
        d_slot_counter++;

        if (output_items.size() > 0) {
            add_item_tag(0, d_next_tag_offset, TIME_KEY, info);
        }

        message_port_pub(MSG_OUT_PORT, info);
        d_tag_offset = d_next_tag_offset;
        d_next_tag_offset += d_tag_interval;
    }

    log_status_summary();
    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace tacmac */
} /* namespace gr */
