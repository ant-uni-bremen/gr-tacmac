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
#include <fmt/format.h>
#include <tacmac/mac_controller.h>

// std::span would be nice -> requires C++20
// #include <span>

namespace gr {
namespace tacmac {

uint64_t parse_timestamp(const std::vector<uint8_t>& bytes)
{
    uint64_t timestamp = 0;
    for (int i = 0; i < 8; ++i) {
        timestamp |= uint64_t(bytes[i]) << ((7 - i) * 8);
    }
    return timestamp;
}

struct ipv4_header {
    /*
     * https://en.wikipedia.org/wiki/IPv4#Packet_structure
     */
    // ipv4_header(std::span<uint8_t> header_bytes){} C++20 solution!
    ipv4_header(uint8_t* header_bytes, unsigned size)
    {
        version = (header_bytes[0] >> 4) & 0x0f;
        ihl = header_bytes[0] & 0x0f;
        dscp = (header_bytes[1] >> 2) & 0x3f;
        ecn = header_bytes[1] & 0x03;
        total_length = 256 * header_bytes[2] + header_bytes[3];
        identification = 256 * header_bytes[4] + header_bytes[5];
        flag_reserved = (header_bytes[6] >> 7) & 0x01;
        flag_df = (header_bytes[6] >> 6) & 0x01;
        flag_mf = (header_bytes[6] >> 5) & 0x01;
        fragment_offset = 256 * (header_bytes[6] & 0x1f) + header_bytes[7];
        ttl = header_bytes[8];
        protocol = header_bytes[9];
        header_checksum = 256 * header_bytes[10] + header_bytes[11];
        src_ip_addr = parse_address(header_bytes + 12);
        dst_ip_addr = parse_address(header_bytes + 16);
        src_ip_string = address_to_string(src_ip_addr);
        dst_ip_string = address_to_string(dst_ip_addr);
    }

    std::string address_to_string(const uint32_t addr)
    {
        return fmt::format("{}.{}.{}.{}",
                           (addr >> 24) & 0xff,
                           (addr >> 16) & 0xff,
                           (addr >> 8) & 0xff,
                           addr & 0xff);
    }

    uint32_t parse_address(uint8_t* bytes)
    {
        uint32_t address = 0;
        uint32_t mask = 0x000000ff;
        for (unsigned i = 0; i < 4; ++i) {
            unsigned leftshift = 8 * (3 - i);
            address += (uint32_t(bytes[i]) << leftshift) & (mask << leftshift);
        }
        return address;
    }

    unsigned version;
    unsigned ihl;          // Internet Header Length
    unsigned dscp;         // Differentiated Services Code Point
    unsigned ecn;          // Explicit Congestion Notification
    uint16_t total_length; // header + payload length in byte [20-65535]
    uint16_t identification;

    // flags
    unsigned flag_reserved; // reserved must be 0
    unsigned flag_df;       // Don't Fragment
    unsigned flag_mf;       // More Fragments

    uint16_t fragment_offset;
    unsigned ttl;      // Time to Live
    unsigned protocol; // L4 protocol.
    unsigned header_checksum;
    uint32_t src_ip_addr;
    std::string src_ip_string;
    uint32_t dst_ip_addr;
    std::string dst_ip_string;
};

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

    uint64_t d_last_phy_ticks = 0;
    uint64_t d_last_llc_ticks = 0;

    enum phy_status_t { OK, NOT_US, LOOPBACK, WRONG_SRC, INVALID_CRC };
    phy_status_t check_phy_packet(const unsigned dst,
                                  const unsigned src,
                                  const uint16_t calced_checksum,
                                  const u_int16_t packet_checksum) const;
    std::string get_status_string(const phy_status_t status) const
    {
        switch (status) {
        case OK:
            return std::string("OK");
        case NOT_US:
            return std::string("Not for us!");
        case LOOPBACK:
            return std::string("Loopback!");
        case WRONG_SRC:
            return std::string("Wrong source!");
        case INVALID_CRC:
            return std::string("Invalid CRC!");
        default:
            return std::string("Missing case!");
        }
    }


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
    const pmt::pmt_t PMT_DSP_LATENCY = pmt::mp("dsp_latency");
    const pmt::pmt_t PMT_ECHO_TICKS = pmt::mp("echo_ticks");

    void print_llc_message_status(const uint64_t ticks);
    void print_phy_message_status(const uint64_t ticks);
    std::string get_host_string()
    {
        return fmt::format("Host({}) -> {}", d_src_id, d_dst_id);
    }

    std::string get_packet_header_string(const unsigned dst,
                                         const unsigned src,
                                         const unsigned sequence,
                                         const unsigned payload_size)
    {
        return fmt::format(
            "PACKET(DST={}, SRC={}, SEQ={}, SIZE={})", dst, src, sequence, payload_size);
    }

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
