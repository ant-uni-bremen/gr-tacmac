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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif


#define CRCPP_USE_CPP11
#include "CRC.h"

#include "mac_controller_impl.h"
#include <gnuradio/io_signature.h>
#include <chrono>
#include <exception>
#include <limits>
#include <string>
// C++20 feature: #include <format>
#include <fmt/core.h>
#include <fmt/ranges.h>


namespace gr {
namespace tacmac {

mac_controller::sptr
mac_controller::make(unsigned destination_id, unsigned source_id, unsigned mtu_size)
{
    return gnuradio::get_initial_sptr(
        new mac_controller_impl(destination_id, source_id, mtu_size));
}


/*
 * The private constructor
 */
mac_controller_impl::mac_controller_impl(unsigned destination_id,
                                         unsigned source_id,
                                         unsigned mtu_size)
    : gr::sync_block("mac_controller",
                     gr::io_signature::make(0, 0, 0),
                     gr::io_signature::make(0, 0, 0)),
      d_dst_id(destination_id),
      d_src_id(source_id),
      d_mtu_size(mtu_size),
      d_tx_frame_counter(0),
      d_rx_frame_counter(std::numeric_limits<uint16_t>::max())
{
    if (d_src_id == d_dst_id) {
        auto err_msg =
            fmt::format("destination_id({}) == src_id({})!", d_dst_id, d_src_id);
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
    }

    if (256 < d_dst_id) {
        auto err_msg = fmt::format("destination_id({}) out-of-range [0, 256)!", d_dst_id);
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
    }

    if (256 < d_src_id) {
        auto err_msg = fmt::format("source_id({}) out-of-range [0, 256)", d_src_id);
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
    }

    if (mtu_size > 256) {
        auto err_msg = fmt::format("mtu_size({}) out-of-range [0, 256)", mtu_size);
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
    }

    message_port_register_out(d_llc_out_port);
    message_port_register_out(d_phy_out_port);
    message_port_register_out(d_timing_out_port);

    message_port_register_in(d_llc_in_port);
    set_msg_handler(d_llc_in_port, [this](pmt::pmt_t msg) { this->handle_llc_msg(msg); });

    message_port_register_in(d_phy_in_port);
    set_msg_handler(d_phy_in_port, [this](pmt::pmt_t msg) { this->handle_phy_msg(msg); });
}

/*
 * Our virtual destructor.
 */
mac_controller_impl::~mac_controller_impl() {}


std::vector<uint8_t> mac_controller_impl::create_header(const size_t frame_counter,
                                                        const uint64_t ticks,
                                                        const unsigned payload_size) const
{
    std::vector<uint8_t> header(4 + 1 + 8);
    header[0] = (uint8_t)d_dst_id;
    header[1] = (uint8_t)d_src_id;
    header[2] = (uint8_t)(frame_counter >> 8) & 0xFF;
    header[3] = (uint8_t)frame_counter & 0xFF;
    header[4] = (uint8_t)payload_size;

    for (int i = 0; i < 8; ++i) {
        header[i + 5] = (uint8_t)(ticks >> ((7 - i) * 8)) & 0xFF;
    }
    return header;
}


uint64_t mac_controller_impl::get_timestamp_ticks_ns_now()
{
    return std::chrono::high_resolution_clock::now().time_since_epoch().count();
}

void mac_controller_impl::print_llc_message_status(const uint64_t ticks)
{
    if (ticks > d_last_llc_print_timestamp + d_print_interval_ticks) {
        const float rate =
            1.0e9 * d_llc_interval_message_counter / (ticks - d_last_llc_print_timestamp);
        const float size =
            1.0 * d_llc_payload_size_counter / d_llc_interval_message_counter;
        GR_LOG_DEBUG(
            this->d_logger,
            fmt::format("LLC: {}: packets: total={}/interval={}\trate={:.1f}P/s; "
                        "packet_size={:.1f}B/{}B",
                        get_host_string(),
                        d_llc_message_counter,
                        d_llc_interval_message_counter,
                        rate,
                        size,
                        d_mtu_size));
        d_llc_interval_message_counter = 0;
        d_llc_payload_size_counter = 0;
        d_last_llc_print_timestamp = ticks;
    }
}

void mac_controller_impl::handle_llc_msg(pmt::pmt_t pdu)
{
    d_llc_message_counter++;
    d_llc_interval_message_counter++;

    const auto frame_counter = d_tx_frame_counter;
    d_tx_frame_counter++;
    d_tx_frame_counter %= std::numeric_limits<uint16_t>::max();

    const uint64_t ticks = get_timestamp_ticks_ns_now();

    std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));
    d_llc_payload_size_counter += payload.size();
    if (payload.size() > d_mtu_size) {
        GR_LOG_WARN(this->d_logger,
                    fmt::format("Dropping PDU, reason: PDU.size={} > MTU.size={}",
                                payload.size(),
                                d_mtu_size));
        return;
    }
    // GR_LOG_DEBUG(this->d_logger,
    //              string_format("LLC: %s: packets=%i;  packet_size=%iB/%iB",
    //                            get_host_string().c_str(),
    //                            d_llc_message_counter,
    //                            payload.size(),
    //                            d_mtu_size));

    auto header = create_header(frame_counter, ticks, payload.size());

    auto meta = flatten_dict(pmt::car(pdu));
    meta = pmt::dict_add(meta, PMT_DST_ID, pmt::from_long(d_dst_id));
    meta = pmt::dict_add(meta, PMT_SRC_ID, pmt::from_long(d_src_id));
    meta = pmt::dict_add(meta, PMT_SEQUENCE, pmt::from_long(frame_counter));
    meta = pmt::dict_add(meta, PMT_TIME, pmt::from_long(ticks));
    meta = pmt::dict_add(meta, PMT_PAYLOAD_SIZE, pmt::from_long(payload.size()));

    payload.insert(payload.begin(), header.begin(), header.end());
    payload.resize(d_mtu_size + header.size(), 0);

    uint16_t checksum =
        CRC::Calculate(payload.data(), payload.size(), CRC::CRC_16_CCITTFALSE());
    payload.push_back((checksum >> 8) & 0xFF);
    payload.push_back(checksum & 0xFF);

    auto pmtpayload = pmt::init_u8vector(payload.size(), payload);

    message_port_pub(d_phy_out_port, pmt::cons(meta, pmtpayload));
    print_llc_message_status(ticks);
}


void mac_controller_impl::print_phy_message_status(const uint64_t ticks)
{
    if (ticks > d_last_phy_print_timestamp + d_print_interval_ticks) {
        const float rate =
            1.0e9 * d_phy_interval_message_counter / (ticks - d_last_phy_print_timestamp);
        const float size =
            1.0 * d_phy_payload_size_counter / d_phy_interval_message_counter;
        const float latency =
            1.0e-6 * d_latency_interval_counter / d_phy_interval_message_counter;
        GR_LOG_DEBUG(
            this->d_logger,
            fmt::format("PHY: {}: packets: total={}/interval={}/lost={}; "
                        "rate={:.1f}P/s; latency={:.3f}ms; packet_size={:.1f}B/{}B",
                        get_host_string(),
                        d_phy_message_counter,
                        d_phy_interval_message_counter,
                        d_lost_packet_interval_counter,
                        rate,
                        latency,
                        size,
                        d_mtu_size));
        d_lost_packet_interval_counter = 0;
        d_latency_interval_counter = 0;
        d_phy_interval_message_counter = 0;
        d_phy_payload_size_counter = 0;
        d_last_phy_print_timestamp = ticks;
    }
}

void mac_controller_impl::handle_phy_msg(pmt::pmt_t pdu)
{
    const std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));

    const uint16_t rx_checksum = (uint16_t(payload[payload.size() - 2] << 8) |
                                  uint16_t(payload[payload.size() - 1]));

    const uint16_t checksum =
        CRC::Calculate(payload.data(), payload.size() - 2, CRC::CRC_16_CCITTFALSE());

    // if (rx_checksum != checksum) {
    //     // C++20 solution: std::string msg = std::format("test {}", 42);
    //     GR_LOG_DEBUG(
    //         this->d_logger,
    //         string_format("CRC16-CCITTFALSE failed! calculated/received: %04X != %04X",
    //                       checksum,
    //                       rx_checksum));

    //     return;
    // }

    const unsigned dst = payload[0];
    const unsigned src = payload[1];
    const unsigned sequence = (uint16_t(payload[2] << 8) | uint16_t(payload[3]));
    const unsigned payload_size = payload[4];

    std::string host_info = get_host_string();
    std::string packet_header =
        get_packet_header_string(dst, src, sequence, payload_size);

    std::string status("OK");

    unsigned status_code = 0;
    if (dst != d_src_id) {
        status = fmt::format(
            "dropping... reason: Not for us! [dst={} != {}=d_src_id]", dst, d_src_id);
        // GR_LOG_DEBUG(this->d_logger,
        //              host_info + " " + packet_header + " " + status);
        status_code = 1;
    }
    if (src == d_src_id) {
        status = fmt::format(
            "dropping... reason: loopback! [src={} == {}=d_src_id]", src, d_src_id);
        // GR_LOG_DEBUG(this->d_logger,
        //              host_info + " " + packet_header + " " + status);
        status_code = 2;
    }
    if (src != d_dst_id) {
        status = fmt::format(
            "dropping... reason: wrong endpoint! [src={} == {}=d_dst_id]", src, d_dst_id);
        // GR_LOG_DEBUG(this->d_logger,
        //              host_info + " " + packet_header + " " + status);
        status_code = 3;
    }
    if (rx_checksum != checksum) {
        // C++20 solution: std::string msg = std::format("test {}", 42);
        status =
            fmt::format("CRC16-CCITTFALSE failed! calculated/received: {:04X} != {:04X}",
                        checksum,
                        rx_checksum);
        status_code = 4;
    }

    GR_LOG_DEBUG(this->d_logger, host_info + " " + packet_header + " " + status);

    if (status_code != 0) {
        GR_LOG_DEBUG(this->d_debug_logger,
                     host_info + " " + packet_header + " " + status);
        return;
    }
    d_phy_message_counter++;
    d_phy_interval_message_counter++;

    const std::vector<uint8_t> data(payload.begin() + 13,
                                    payload.begin() + 13 + payload_size);

    auto meta = flatten_dict(pmt::car(pdu));
    meta = pmt::dict_add(meta, PMT_DST_ID, pmt::from_long(dst));
    meta = pmt::dict_add(meta, PMT_SRC_ID, pmt::from_long(src));
    meta = pmt::dict_add(meta, PMT_SEQUENCE, pmt::from_long(sequence));
    meta = pmt::dict_add(meta, PMT_PAYLOAD_SIZE, pmt::from_long(payload_size));
    const unsigned lost_packets =
        (sequence - d_rx_frame_counter - 1) % std::numeric_limits<uint16_t>::max();
    d_rx_frame_counter = sequence;
    meta = pmt::dict_add(meta, PMT_LOST_PACKETS, pmt::from_long(lost_packets));

    uint64_t timestamp = 0;
    for (int i = 0; i < 8; ++i) {
        timestamp |= uint64_t(payload[i + 5]) << ((7 - i) * 8);
    }
    meta = pmt::dict_add(meta, PMT_TIME, pmt::from_long(timestamp));

    const uint64_t ticks = get_timestamp_ticks_ns_now();
    const uint64_t latency_ticks = ticks - timestamp;
    meta = pmt::dict_add(meta, PMT_LATENCY, pmt::from_long(latency_ticks));
    d_phy_payload_size_counter += data.size();
    d_latency_interval_counter += latency_ticks;
    d_lost_packet_interval_counter += lost_packets;

    message_port_pub(d_llc_out_port,
                     pmt::cons(meta, pmt::init_u8vector(data.size(), data)));


    auto timing_msg = pmt::dict_add(pmt::make_dict(), PMT_DST_ID, pmt::from_long(dst));
    timing_msg = pmt::dict_add(timing_msg, PMT_SRC_ID, pmt::from_long(src));
    timing_msg = pmt::dict_add(timing_msg, PMT_SEQUENCE, pmt::from_long(sequence));
    timing_msg = pmt::dict_add(timing_msg, PMT_TIME, pmt::from_long(timestamp));
    timing_msg = pmt::dict_add(
        timing_msg, PMT_RX_TIME, pmt::dict_ref(meta, PMT_RX_TIME, pmt::from_long(0)));
    timing_msg = pmt::dict_add(timing_msg, PMT_RX_MAC_TIME, pmt::from_long(ticks));
    message_port_pub(d_timing_out_port, timing_msg);
    print_phy_message_status(ticks);
}

int mac_controller_impl::work(int noutput_items,
                              gr_vector_const_void_star& input_items,
                              gr_vector_void_star& output_items)
{
    // This should never be called! This is a PDU only block!
    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace tacmac */
} /* namespace gr */
