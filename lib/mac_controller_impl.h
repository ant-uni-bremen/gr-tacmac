/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifndef INCLUDED_TACMAC_MAC_CONTROLLER_IMPL_H
#define INCLUDED_TACMAC_MAC_CONTROLLER_IMPL_H

#include "tacmac_utilities.h"
#include <tacmac/mac_controller.h>

namespace gr {
namespace tacmac {

/*
 * This is a C++11 solution to obtain formatted strings.
 *
 * Source: https://stackoverflow.com/a/26221725 under CC0
 *
 * As noted in the source this boils down to:
 * std::format() with C++20!
 */
// template <typename... Args>
// std::string string_format(const std::string& format, Args... args)
// {
//     size_t size =
//         snprintf(nullptr, 0, format.c_str(), args...) + 1; // Extra space for '\0'
//     if (size <= 0) {
//         throw std::runtime_error("Error during formatting.");
//     }
//     std::unique_ptr<char[]> buf(new char[size]);
//     snprintf(buf.get(), size, format.c_str(), args...);
//     return std::string(buf.get(), buf.get() + size - 1); // We don't want the '\0'
//     inside
// }

class mac_controller_impl : public mac_controller
{
private:
    const unsigned d_dst_id;
    const unsigned d_src_id;
    const unsigned d_mtu_size;
    size_t d_tx_frame_counter;
    size_t d_rx_frame_counter;

    const uint64_t d_print_interval_ticks = 2000000000ull;
    uint64_t d_last_llc_print_timestamp = 0;
    uint64_t d_llc_message_counter = 0;
    uint64_t d_llc_interval_message_counter = 0;
    uint64_t d_llc_payload_size_counter = 0;

    uint64_t d_last_phy_print_timestamp = 0;
    uint64_t d_phy_message_counter = 0;
    uint64_t d_phy_interval_message_counter = 0;
    uint64_t d_phy_payload_size_counter = 0;
    uint64_t d_latency_interval_counter = 0;
    uint64_t d_lost_packet_interval_counter = 0;


    std::vector<uint8_t> create_header(const size_t frame_counter,
                                       const uint64_t ticks,
                                       const unsigned payload_size) const;

    const pmt::pmt_t d_llc_in_port = pmt::mp("LLCin");
    const pmt::pmt_t d_llc_out_port = pmt::mp("LLCout");
    const pmt::pmt_t d_phy_in_port = pmt::mp("PHYin");
    const pmt::pmt_t d_phy_out_port = pmt::mp("PHYout");
    const pmt::pmt_t d_timing_out_port = pmt::mp("timing");

    const pmt::pmt_t PMT_DST_ID = pmt::mp("dst_id");
    const pmt::pmt_t PMT_SRC_ID = pmt::mp("src_id");
    const pmt::pmt_t PMT_SEQUENCE = pmt::mp("sequence");
    const pmt::pmt_t PMT_TIME = pmt::mp("time");
    const pmt::pmt_t PMT_RX_TIME = pmt::mp("rx_time");
    const pmt::pmt_t PMT_RX_MAC_TIME = pmt::mp("rx_mac_time");
    const pmt::pmt_t PMT_PAYLOAD_SIZE = pmt::mp("payload_size");
    const pmt::pmt_t PMT_LOST_PACKETS = pmt::mp("lost_packets");
    const pmt::pmt_t PMT_LATENCY = pmt::mp("latency");

    pmt::pmt_t flatten_dict(const pmt::pmt_t& dict) const;
    void print_llc_message_status(const uint64_t ticks);
    void print_phy_message_status(const uint64_t ticks);
    std::string get_host_string()
    {
        return string_format("Host(%i) -> %i", d_src_id, d_dst_id);
    }

    std::string get_packet_header_string(const unsigned dst,
                                         const unsigned src,
                                         const unsigned sequence,
                                         const unsigned payload_size)
    {
        return string_format(
            "PACKET(DST=%i, SRC=%i, SEQ=%i, SIZE=%i)", dst, src, sequence, payload_size);
    }

    uint64_t get_timestamp_ticks_ns_now();

public:
    mac_controller_impl(unsigned destination_id, unsigned source_id, unsigned mtu_size);
    ~mac_controller_impl();

    // Where all the action really happens
    void handle_llc_msg(pmt::pmt_t pdu);
    void handle_phy_msg(pmt::pmt_t pdu);

    // Dummy!
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_MAC_CONTROLLER_IMPL_H */
