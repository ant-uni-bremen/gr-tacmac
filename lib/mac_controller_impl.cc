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
    if (256 < d_dst_id) {
        std::string err_msg("destination_id(" + std::to_string(d_dst_id) +
                            ") out-of-range [0, 256)!");
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
    }

    if (256 < d_src_id) {
        std::string err_msg("source_id(" + std::to_string(d_src_id) +
                            ") out-of-range [0, 256)");
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
    }

    if (mtu_size > 256) {
        std::string err_msg("mtu_size(" + std::to_string(mtu_size) +
                            ") out-of-range [0, 256)");
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
    }

    message_port_register_out(d_llc_out_port);
    message_port_register_out(d_phy_out_port);

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
                                                        const unsigned payload_size)
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


void mac_controller_impl::handle_llc_msg(pmt::pmt_t pdu)
{
    // const auto llc_start = std::chrono::high_resolution_clock::now();

    const auto frame_counter = d_tx_frame_counter;
    d_tx_frame_counter++;
    d_tx_frame_counter %= std::numeric_limits<uint16_t>::max();

    const auto since_epoch = std::chrono::high_resolution_clock::now().time_since_epoch();
    const uint64_t ticks = since_epoch.count();

    std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));
    if (payload.size() > d_mtu_size) {
        GR_LOG_WARN(this->d_logger,
                    string_format("Dropping PDU, reason: PDU.size=%i > MTU.size=%i",
                                  payload.size(),
                                  d_mtu_size));
        return;
    }
    auto header = create_header(frame_counter, ticks, payload.size());
    // GR_LOG_INFO(this->d_logger, string_format("payload.size=%i", payload.size()));

    // const auto header_duration =
    // std::chrono::nanoseconds(std::chrono::high_resolution_clock::now() - llc_start);

    auto meta = pmt::car(pdu);
    meta = pmt::dict_add(meta, PMT_DST_ID, pmt::from_long(d_dst_id));
    meta = pmt::dict_add(meta, PMT_SRC_ID, pmt::from_long(d_src_id));
    meta = pmt::dict_add(meta, PMT_SEQUENCE, pmt::from_long(frame_counter));
    meta = pmt::dict_add(meta, PMT_TIME, pmt::from_long(ticks));
    meta = pmt::dict_add(meta, PMT_PAYLOAD_SIZE, pmt::from_long(payload.size()));

    // const auto meta_duration =
    // std::chrono::nanoseconds(std::chrono::high_resolution_clock::now() - llc_start);


    payload.insert(payload.begin(), header.begin(), header.end());
    payload.resize(d_mtu_size + header.size(), 0);

    uint16_t checksum =
        CRC::Calculate(payload.data(), payload.size(), CRC::CRC_16_CCITTFALSE());
    payload.push_back((checksum >> 8) & 0xFF);
    payload.push_back(checksum & 0xFF);

    // const auto payload_duration =
    // std::chrono::nanoseconds(std::chrono::high_resolution_clock::now() - llc_start);

    auto pmtpayload = pmt::init_u8vector(payload.size(), payload);
    // const auto pmtvec_duration =
    // std::chrono::nanoseconds(std::chrono::high_resolution_clock::now() - llc_start);

    message_port_pub(d_phy_out_port, pmt::cons(meta, pmtpayload));

    // const auto llc_duration =
    //     std::chrono::nanoseconds(std::chrono::high_resolution_clock::now() -
    //     llc_start);

    // GR_LOG_INFO(this->d_logger, "LLC header duration: " +
    //                             std::to_string(header_duration.count()) +
    //                             "ns");
    // GR_LOG_INFO(this->d_logger, "LLC meta duration: " +
    //                             std::to_string(meta_duration.count()) +
    //                             "ns");
    // GR_LOG_INFO(this->d_logger, "LLC payload duration: " +
    //                             std::to_string(payload_duration.count()) +
    //                             "ns");
    // GR_LOG_INFO(this->d_logger, "LLC pmtvec duration: " +
    //                             std::to_string(pmtvec_duration.count()) +
    //                             "ns");

    // GR_LOG_INFO(this->d_logger,
    //             "LLC duration: " + std::to_string(llc_duration.count() * 1.0e-3) +
    //             "us");
}


void mac_controller_impl::handle_phy_msg(pmt::pmt_t pdu)
{
    // const auto phy_start = std::chrono::high_resolution_clock::now();

    const std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));

    const uint16_t rx_checksum = (uint16_t(payload[payload.size() - 2] << 8) |
                                  uint16_t(payload[payload.size() - 1]));

    const uint16_t checksum =
        CRC::Calculate(payload.data(), payload.size() - 2, CRC::CRC_16_CCITTFALSE());

    if (rx_checksum != checksum) {
        // C++20 solution: std::string msg = std::format("test {}", 42);
        GR_LOG_DEBUG(
            this->d_logger,
            string_format("CRC16-CCITTFALSE failed! calculated/received: %04X != %04X",
                          checksum,
                          rx_checksum));

        return;
    }

    const unsigned dst = payload[0];
    const unsigned src = payload[1];
    const unsigned sequence = (uint16_t(payload[2] << 8) | uint16_t(payload[3]));
    const unsigned payload_size = payload[4];

    std::string host_info = string_format("Host(%i)", d_src_id);
    std::string packet_header =
        string_format("PACKET(DST=%i, SRC=%i, SEQ=%i)", dst, src, sequence);

    std::string status("OK");

    unsigned status_code = 0;
    if (dst != d_src_id) {
        status = string_format(
            "dropping... reason: Not for us! [dst=%i != %i=d_src_id]", dst, d_src_id);
        status_code = 1;
    }
    if (src == d_src_id) {
        status = string_format(
            "dropping... reason: loopback! [src=%i == %i=d_src_id]", src, d_src_id);
        status_code = 2;
    }

    if (status_code != 0) {
        GR_LOG_DEBUG(this->d_logger, host_info + " " + packet_header + " " + status);
        return;
    }

    const std::vector<uint8_t> data(payload.begin() + 13,
                                    payload.begin() + 13 + payload_size);

    auto meta = pmt::car(pdu);
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
    const auto since_epoch = std::chrono::high_resolution_clock::now().time_since_epoch();
    const uint64_t ticks = since_epoch.count();
    meta = pmt::dict_add(meta, PMT_LATENCY, pmt::from_long(ticks - timestamp));

    message_port_pub(d_llc_out_port,
                     pmt::cons(meta, pmt::init_u8vector(data.size(), data)));

    // double lat = (ticks - timestamp) * 1.0e-6;
    // std::chrono::duration<double> looplat = d_phy_last - d_llc_last;
    // GR_LOG_DEBUG(this->d_logger,
    //              host_info + " " + packet_header + " " +
    //                  string_format("latency=%.4fms", lat) +
    //                  " loop: " + std::to_string(looplat.count()) + "s");
    // const auto phy_duration =
    //     std::chrono::nanoseconds(std::chrono::high_resolution_clock::now() -
    //     phy_start);
    // GR_LOG_INFO(this->d_logger,
    //             "PHY duration: " + std::to_string(phy_duration.count() * 1.0e-3) +
    //             "us");
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
