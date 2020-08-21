/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "status_collector_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace tacmac {

// #pragma message("set the following appropriately and remove this warning")
using input_type = float;
// #pragma message("set the following appropriately and remove this warning")
using output_type = float;
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

void status_collector_impl::handle_pdu_meta(const pmt::pmt_t& meta)
{
    if (pmt::dict_has_key(meta, pmt::mp("tx_time"))) {
        return;
    }
    long lost_packets =
        pmt::to_long(pmt::dict_ref(meta, pmt::mp("lost_packets"), pmt::from_long(-1)));
    if (lost_packets != 0) {
        GR_LOG_DEBUG(d_logger, "### META ###");
        for (size_t i = 0; i < pmt::length(meta); i++) {
            auto k = pmt::car(pmt::nth(i, meta));
            auto v = pmt::cdr(pmt::nth(i, meta));
            if (not pmt::is_uniform_vector(v)) {
                GR_LOG_DEBUG(d_logger,
                             string_format("PDU: key=%s\tvalue=%s",
                                           pmt::write_string(k).c_str(),
                                           pmt::write_string(v).c_str()));
            }
        }
        GR_LOG_DEBUG(d_logger, "### META END ###");
    }
}

void status_collector_impl::handle_uhd_tx(const pmt::pmt_t& msg)
{
    GR_LOG_DEBUG(d_logger, "UHD_TX: " + pmt::write_string(msg));
    auto time_spec = pmt::dict_ref(msg, pmt::mp("tx_time"), pmt::mp("NA"));
    d_tx_full_secs = pmt::to_uint64(pmt::tuple_ref(time_spec, 0));
    d_tx_frac_secs = pmt::to_double(pmt::tuple_ref(time_spec, 1));
}
void status_collector_impl::handle_uhd_tx_async(const pmt::pmt_t& msg)
{
    // GR_LOG_DEBUG(d_logger, "ASYNC:  " + pmt::write_string(msg));
    auto data = pmt::cdr(msg);
    // GR_LOG_DEBUG(d_logger, pmt::write_string(data));
    auto event_code_list =
        pmt::dict_ref(data, pmt::intern("event_code"), pmt::intern("NA"));
    std::vector<std::string> event_codes;
    for (int i = 0; i < pmt::length(event_code_list); i++) {
        event_codes.push_back(pmt::symbol_to_string(pmt::nth(i, event_code_list)));
    }

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
    has_error_event = true;
    if (has_error_event) {
        GR_LOG_DEBUG(
            d_logger,
            string_format(
                "UHD_ASYNC: "
                "RXtime=%s\tTXtime=%s\tevent_time=%s\tchannel=%i\tevent_codes=%s",
                get_formatted_time_spec(d_full_secs, d_frac_secs).c_str(),
                get_formatted_time_spec(d_tx_full_secs, d_tx_frac_secs).c_str(),
                get_formatted_time_spec(d_async_full_secs, d_async_frac_secs).c_str(),
                channel,
                event_codes_string.c_str()));
    }
}

void status_collector_impl::handle_msg(pmt::pmt_t msg)
{
    if (pmt::is_tuple(msg)) {
        d_full_secs = pmt::to_uint64(pmt::tuple_ref(msg, 0));
        d_frac_secs = pmt::to_double(pmt::tuple_ref(msg, 1));
        d_time_ticks = timespec2ticks(d_full_secs, d_frac_secs);
        d_tag_offset = pmt::to_uint64(pmt::tuple_ref(msg, 2));
        d_samp_rate = pmt::to_double(pmt::tuple_ref(msg, 3));
        d_slot_counter = pmt::to_uint64(pmt::tuple_ref(msg, 4));
    } else if (pmt::is_pdu(msg)) {
        handle_pdu_meta(pmt::car(msg));
    } else if (pmt::is_dict(msg) && pmt::dict_has_key(msg, pmt::mp("tx_time"))) {
        handle_uhd_tx(msg);

    } else if (pmt::is_pair(msg) && pmt::eq(pmt::car(msg), UHD_ASYNC_MSG_KEY)) {
        handle_uhd_tx_async(msg);
        // GR_LOG_DEBUG(d_logger, pmt::write_string(msg));
        // auto data = pmt::cdr(msg);
        // // GR_LOG_DEBUG(d_logger, pmt::write_string(data));
        // auto event_code_list =
        //     pmt::dict_ref(data, pmt::intern("event_code"), pmt::intern("NA"));
        // std::vector<std::string> event_codes;
        // for (int i = 0; i < pmt::length(event_code_list); i++) {
        //     event_codes.push_back(pmt::symbol_to_string(pmt::nth(i, event_code_list)));
        // }

        // std::string event_codes_string = "'" + event_codes[0] + "'";
        // bool has_error_event = event_codes[0] != "burst_ack";
        // for (int i = 1; i < event_codes.size(); i++) {
        //     event_codes_string += ", '" + event_codes[i] + "'";
        //     has_error_event |= event_codes[i] != "burst_ack";
        // }

        // auto channel = pmt::to_uint64(
        //     pmt::dict_ref(data, pmt::mp("channel"), pmt::from_uint64(8 * 8 * 8 * 8)));
        // //     GR_LOG_DEBUG(d_logger, "channel=" + std::to_string(channel));
        // auto time_spec = pmt::dict_ref(data, pmt::mp("time_spec"), pmt::mp("NA"));
        // auto full_secs = pmt::to_long(pmt::car(time_spec));
        // auto frac_secs = pmt::to_double(pmt::cdr(time_spec));
        // if (has_error_event) {
        //     GR_LOG_DEBUG(
        //         d_logger,
        //         string_format(
        //             "UHD_ASYNC: RXtime=%s\tevent_time=%s\tchannel=%i\tevent_codes=%s",
        //             get_formatted_time_spec(d_full_secs, d_frac_secs).c_str(),
        //             get_formatted_time_spec(full_secs, frac_secs).c_str(),
        //             channel,
        //             event_codes_string.c_str()));
        // }

    } else {
        GR_LOG_DEBUG(d_logger, pmt::write_string(msg));
    }

    message_port_pub(d_out_port, msg);
} // namespace tacmac

int status_collector_impl::work(int noutput_items,
                                gr_vector_const_void_star& input_items,
                                gr_vector_void_star& output_items)
{
    // const input_type *in = reinterpret_cast<const input_type*>(input_items[0]);
    // output_type *out = reinterpret_cast<output_type*>(output_items[0]);

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} // namespace tacmac
} /* namespace gr */
