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
#include <random>
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

namespace {
std::vector<uint8_t> initialize_random_bit_vector(const unsigned size,
                                                  const unsigned seed = 4711)
{
    std::mt19937 mersenne_engine;
    mersenne_engine.seed(seed);
    std::uniform_int_distribution<uint8_t> dist{ 0, 255 };
    auto gen = [&dist, &mersenne_engine]() { return dist(mersenne_engine); };

    std::vector<uint8_t> vec(size);
    std::generate(begin(vec), end(vec), gen);
    return vec;
}
} // namespace

std::tuple<unsigned, unsigned, unsigned, unsigned, uint16_t>
parse_payload(const std::vector<uint8_t>& payload)
{
    const uint16_t checksum = (uint16_t(payload[payload.size() - 2] << 8) |
                               uint16_t(payload[payload.size() - 1]));

    const unsigned dst = payload[0];
    const unsigned src = payload[1];
    const unsigned sequence = (uint16_t(payload[2] << 8) | uint16_t(payload[3]));
    const unsigned payload_size = payload[4];
    return { dst, src, sequence, payload_size, checksum };
}


uint16_t calculate_checksum(const std::vector<uint8_t>& payload,
                            unsigned num_ignored_tail_bytes)
{
    return CRC::Calculate(payload.data(),
                          payload.size() - num_ignored_tail_bytes,
                          CRC::CRC_16_CCITTFALSE());
}

void mac_controller_impl::handle_llc_msg(pmt::pmt_t pdu)
{
    d_llc_message_counter++;
    d_llc_interval_message_counter++;

    const auto frame_counter = d_tx_frame_counter;
    d_tx_frame_counter++;
    d_tx_frame_counter %= std::numeric_limits<uint16_t>::max();

    const uint64_t ticks = get_timestamp_ticks_ns_now();
    const uint64_t echo_ticks = ticks - d_last_phy_ticks;
    d_last_llc_ticks = ticks;

    std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));
    d_llc_payload_size_counter += payload.size();
    if (payload.size() > d_mtu_size) {
        GR_LOG_WARN(this->d_logger,
                    fmt::format("Dropping PDU, reason: PDU.size={} > MTU.size={}",
                                payload.size(),
                                d_mtu_size));
        return;
    }

    // const float rtt = 1.0e-6 * (ticks - d_last_phy_ticks);
    // GR_LOG_DEBUG(this->d_logger,
    //              fmt::format("{}\tLLC: {}: packet: {:2}->{:2} (#={:5})\t{:.4f}ms",
    //                          ticks,
    //                          get_host_string(),
    //                          d_src_id,
    //                          d_dst_id,
    //                          frame_counter,
    //                          rtt));

    // auto ip_header = ipv4_header(payload.data(), 20);
    // fmt::print("{} -> {}: IPv{}, length={}B, ihl={} ({}B), protocol={}, TTL={},
    // DSCP={}, "
    //            "ECN={}, ID={}, flags=(R={}, DF={}, MF{}), FragmentOffset={}\n",
    //            ip_header.src_ip_string,
    //            ip_header.dst_ip_string,
    //            ip_header.version,
    //            ip_header.total_length,
    //            ip_header.ihl,
    //            ip_header.ihl * 4,
    //            ip_header.protocol,
    //            ip_header.ttl,
    //            ip_header.dscp,
    //            ip_header.ecn,
    //            ip_header.identification,
    //            ip_header.flag_reserved,
    //            ip_header.flag_df,
    //            ip_header.flag_mf,
    //            ip_header.fragment_offset);
    auto header = create_header(frame_counter, ticks, payload.size());
    if (d_replay_mode_active) {
        header = create_header(4711, 0xC0FFEE42, d_mtu_size);
        payload = initialize_random_bit_vector(d_mtu_size);
    }

    auto meta = flatten_dict(pmt::car(pdu));
    meta = pmt::dict_add(meta, PMT_DST_ID, pmt::from_long(d_dst_id));
    meta = pmt::dict_add(meta, PMT_SRC_ID, pmt::from_long(d_src_id));
    meta = pmt::dict_add(meta, PMT_SEQUENCE, pmt::from_long(frame_counter));
    meta = pmt::dict_add(meta, PMT_TIME, pmt::from_long(ticks));
    meta = pmt::dict_add(meta, PMT_PAYLOAD_SIZE, pmt::from_long(payload.size()));
    meta = pmt::dict_add(meta, PMT_ECHO_TICKS, pmt::from_long(echo_ticks));

    payload.insert(payload.begin(), header.begin(), header.end());
    payload.resize(d_mtu_size + header.size(), 0);

    const uint16_t checksum = calculate_checksum(payload);
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

mac_controller_impl::phy_status_t
mac_controller_impl::check_phy_packet(const unsigned dst,
                                      const unsigned src,
                                      const uint16_t calced_checksum,
                                      const u_int16_t packet_checksum) const
{
    auto status = phy_status_t::OK;
    if (dst != d_src_id) {
        status = phy_status_t::NOT_US;
    }
    if (src == d_src_id) {
        status = phy_status_t::LOOPBACK;
    }
    if (src != d_dst_id) {
        status = phy_status_t::WRONG_SRC;
    }
    if (packet_checksum != calced_checksum) {
        status = phy_status_t::INVALID_CRC;
    }
    return status;
}

void mac_controller_impl::handle_phy_msg(pmt::pmt_t pdu)
{
    const std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));

    auto [dst, src, sequence, payload_size, rx_checksum] = parse_payload(payload);

    const auto checksum = calculate_checksum(payload, 2);

    const auto status_code = check_phy_packet(dst, src, checksum, rx_checksum);

    if (status_code != phy_status_t::OK) {
        const std::string host_info = get_host_string();
        const std::string packet_header =
            get_packet_header_string(dst, src, sequence, payload_size);
        const auto status =
            fmt::format("packet status: {} [packet(src={}, dst={}), controller(src={}, "
                        "dst={}), CRC(received={:04X}, calculated={:04X})]",
                        get_status_string(status_code),
                        src,
                        dst,
                        d_src_id,
                        d_dst_id,
                        rx_checksum,
                        checksum);
        GR_LOG_DEBUG(this->d_logger,
                     fmt::format("{} {} {}", host_info, packet_header, status));
        // if (status_code != phy_status_t::OK) {
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

    const uint64_t timestamp =
        parse_timestamp({ payload.begin() + 5, payload.begin() + 5 + 8 });

    meta = pmt::dict_add(meta, PMT_TIME, pmt::from_long(timestamp));

    const uint64_t ticks = get_timestamp_ticks_ns_now();
    d_last_phy_ticks = ticks;
    const uint64_t latency_ticks =
        (ticks >= timestamp) ? (ticks - timestamp) : (timestamp - ticks);
    meta = pmt::dict_add(meta, PMT_LATENCY, pmt::from_long(latency_ticks));
    d_phy_payload_size_counter += data.size();
    d_latency_interval_counter += latency_ticks;
    d_lost_packet_interval_counter += lost_packets;

    // The RX packet metadata keys are suffixed with a number at this point. It goes
    // from 0 ... N-1 RX streams.
    const uint64_t rx_dsp_latency =
        pmt::to_uint64(pmt::dict_ref(meta, pmt::mp("time0"), pmt::from_uint64(0)));
    meta = pmt::dict_add(meta, PMT_DSP_LATENCY, pmt::from_long(rx_dsp_latency));

    // const float dsp_latency_ms = 1.0e-6 * (ticks - rx_dsp_latency);
    // const float rtt = 1.0e-6 * (ticks - d_last_llc_ticks);
    // GR_LOG_DEBUG(
    //     this->d_logger,
    //     fmt::format("{}\tPHY: {}: packet: {:2}->{:2} (#={:5})\t{:.4f}ms\t{:.4f}ms",
    //                 ticks,
    //                 get_host_string(),
    //                 src,
    //                 dst,
    //                 sequence,
    //                 rtt,
    //                 dsp_latency_ms));

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
