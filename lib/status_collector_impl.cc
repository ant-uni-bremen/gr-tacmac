/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "status_collector_impl.h"
#include <gnuradio/io_signature.h>
#include <fmt/core.h>

namespace gr {
namespace tacmac {

status_collector::sptr status_collector::make()
{
    return gnuradio::get_initial_sptr(new status_collector_impl());
}


/*
 * The private constructor
 */
status_collector_impl::status_collector_impl()
    : gr::sync_block("status_collector",
                     gr::io_signature::make(0, 0, 0),
                     gr::io_signature::make(0, 0, 0))
{
    message_port_register_out(d_out_port);

    message_port_register_in(d_in_port);
    set_msg_handler(d_in_port, [this](pmt::pmt_t msg) { this->handle_msg(msg); });
}

/*
 * Our virtual destructor.
 */
status_collector_impl::~status_collector_impl() {}

pmt::pmt_t status_collector_impl::handle_pdu_meta(const pmt::pmt_t& meta)
{
    if (pmt::dict_has_key(meta, pmt::mp("tx_time"))) {
        return pmt::PMT_F;
    }
    auto status = pmt::make_dict();
    for (size_t i = 0; i < pmt::length(meta); i++) {
        auto k = pmt::car(pmt::nth(i, meta));
        auto v = pmt::cdr(pmt::nth(i, meta));
        if (not pmt::is_uniform_vector(v)) {
            status = pmt::dict_add(status, k, v);
        }
    }
    return pmt::cons(RX_MSG_KEY, status);
}

pmt::pmt_t status_collector_impl::handle_uhd_tx(const pmt::pmt_t& msg)
{
    auto status = pmt::make_dict();
    // GR_LOG_DEBUG(d_logger, "UHD_TX: " + pmt::write_string(msg));
    auto time_spec = pmt::dict_ref(msg, pmt::mp("tx_time"), pmt::mp("NA"));
    d_tx_full_secs = pmt::to_uint64(pmt::tuple_ref(time_spec, 0));
    d_tx_frac_secs = pmt::to_double(pmt::tuple_ref(time_spec, 1));
    auto time_ticks = timespec2ticks(d_tx_full_secs, d_tx_frac_secs);
    for (size_t i = 0; i < pmt::length(msg); i++) {
        auto k = pmt::car(pmt::nth(i, msg));
        auto v = pmt::cdr(pmt::nth(i, msg));
        if (not pmt::is_uniform_vector(v)) {
            status = pmt::dict_add(status, k, v);
        }
    }
    return pmt::cons(UHD_TX_MSG_KEY, status);
}

pmt::pmt_t status_collector_impl::handle_uhd_tx_async(const pmt::pmt_t& msg)
{
    // GR_LOG_DEBUG(d_logger, "ASYNC:  " + pmt::write_string(msg));
    auto status = pmt::make_dict();
    auto data = pmt::cdr(msg);
    // GR_LOG_DEBUG(d_logger, pmt::write_string(data));
    auto event_code_list =
        pmt::dict_ref(data, pmt::intern("event_code"), pmt::intern("NA"));
    std::vector<std::string> event_codes;
    for (int i = 0; i < pmt::length(event_code_list); i++) {
        event_codes.push_back(pmt::symbol_to_string(pmt::nth(i, event_code_list)));
    }
    for (size_t i = 0; i < pmt::length(data); i++) {
        auto k = pmt::car(pmt::nth(i, data));
        auto v = pmt::cdr(pmt::nth(i, data));
        if (not pmt::is_uniform_vector(v)) {
            status = pmt::dict_add(status, k, v);
        }
    }
    status =
        pmt::dict_add(status, pmt::intern("event_code"), pmt::nth(0, event_code_list));

    std::string event_codes_string = "'" + event_codes[0] + "'";
    bool has_error_event = event_codes[0] != "burst_ack";
    for (int i = 1; i < event_codes.size(); i++) {
        event_codes_string += ", '" + event_codes[i] + "'";
        has_error_event |= event_codes[i] != "burst_ack";
    }

    auto channel = pmt::to_uint64(
        pmt::dict_ref(data, pmt::mp("channel"), pmt::from_uint64(8 * 8 * 8 * 8)));
    //     GR_LOG_DEBUG(d_logger, "channel=" + std::to_string(channel));
    auto time_spec = pmt::dict_ref(data, pmt::mp("time_spec"), pmt::mp("NA"));
    d_async_full_secs = pmt::to_long(pmt::car(time_spec));
    d_async_frac_secs = pmt::to_double(pmt::cdr(time_spec));
    status = pmt::dict_add(
        status,
        pmt::intern("time"),
        pmt::from_uint64(timespec2ticks(d_async_full_secs, d_async_frac_secs)));
    // has_error_event = true;
    // if (has_error_event) {
    //     GR_LOG_DEBUG(
    //         d_logger,
    //         string_format(
    //             "UHD_ASYNC: "
    //             "RXtime=%s\tTXtime=%s\tevent_time=%s\tchannel=%i\tevent_codes=%s",
    //             get_formatted_time_spec(d_full_secs, d_frac_secs).c_str(),
    //             get_formatted_time_spec(d_tx_full_secs, d_tx_frac_secs).c_str(),
    //             get_formatted_time_spec(d_async_full_secs, d_async_frac_secs).c_str(),
    //             channel,
    //             event_codes_string.c_str()));
    // }
    return pmt::cons(UHD_ASYNC_MSG_KEY, status);
}

void status_collector_impl::handle_msg(pmt::pmt_t msg)
{
    pmt::pmt_t status = pmt::PMT_F;
    if (pmt::is_tuple(msg)) {
        d_full_secs = pmt::to_uint64(pmt::tuple_ref(msg, 0));
        d_frac_secs = pmt::to_double(pmt::tuple_ref(msg, 1));
        d_time_ticks = timespec2ticks(d_full_secs, d_frac_secs);
        d_tag_offset = pmt::to_uint64(pmt::tuple_ref(msg, 2));
        d_samp_rate = pmt::to_double(pmt::tuple_ref(msg, 3));
        d_slot_counter = pmt::to_uint64(pmt::tuple_ref(msg, 4));
    } else if (pmt::is_pdu(msg)) {
        status = handle_pdu_meta(flatten_dict(pmt::car(msg)));
    } else if (pmt::is_dict(msg) && pmt::dict_has_key(msg, pmt::mp("tx_time"))) {
        status = handle_uhd_tx(msg);

    } else if (pmt::is_pair(msg) && pmt::eq(pmt::car(msg), UHD_ASYNC_MSG_KEY)) {
        status = handle_uhd_tx_async(msg);
    } else {
        GR_LOG_DEBUG(d_logger, pmt::write_string(msg));
    }

    // auto car = pmt::car(status);
    // auto cdr = pmt::cdr(status);
    // for (size_t i = 0; i < pmt::length(cdr); i++) {
    //     auto k = pmt::car(pmt::nth(i, cdr));
    //     auto v = pmt::cdr(pmt::nth(i, cdr));
    //     GR_LOG_DEBUG(d_logger, pmt::write_string(car) + ":\t" +
    //     pmt::write_string(k) + "\t" + pmt::write_string(v));
    // }


    message_port_pub(d_out_port, status);
}

int status_collector_impl::work(int noutput_items,
                                gr_vector_const_void_star& input_items,
                                gr_vector_void_star& output_items)
{
    // This is a PDU block. `work` should never be called!
    return noutput_items;
}

} // namespace tacmac
} /* namespace gr */
