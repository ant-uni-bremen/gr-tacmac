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

#include <gnuradio/io_signature.h>
#include "mac_controller_impl.h"
#include <exception>
#include <string>
#include <limits>
#include <chrono>

namespace gr {
  namespace tacmac {

    mac_controller::sptr
    mac_controller::make(unsigned destination_id, unsigned source_id)
    {
      return gnuradio::get_initial_sptr
        (new mac_controller_impl(destination_id, source_id));
    }


    /*
     * The private constructor
     */
    mac_controller_impl::mac_controller_impl(unsigned destination_id, unsigned source_id)
      : gr::sync_block("mac_controller",
              gr::io_signature::make(0, 0, 0),
              gr::io_signature::make(0, 0, 0)),
              d_dst_id(destination_id),
              d_src_id(source_id),
              d_tx_frame_counter(0),
              d_rx_frame_counter(std::numeric_limits<uint16_t>::max()),
              d_llc_in_port(pmt::mp("LLCin")),
              d_llc_out_port(pmt::mp("LLCout")),
              d_phy_in_port(pmt::mp("PHYin")),
              d_phy_out_port(pmt::mp("PHYout"))
    {
      if(256 < d_dst_id){
        std::string err_msg("destination_id(");
        err_msg += std::to_string(d_dst_id);
        err_msg += ") out-of-range [0, 256)!";
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
      }

      if(256 < d_src_id){
        std::string err_msg("source_id(");
        err_msg += std::to_string(d_src_id);
        err_msg += ") out-of-range [0, 256)";
        GR_LOG_ERROR(this->d_logger, err_msg);
        throw std::invalid_argument(err_msg);
      }

      message_port_register_out(d_llc_out_port);
      message_port_register_out(d_phy_out_port);

      message_port_register_in(d_llc_in_port);
      set_msg_handler(d_llc_in_port,
                    boost::bind(&mac_controller_impl::handle_llc_msg, this, _1));

      message_port_register_in(d_phy_in_port);
      set_msg_handler(d_phy_in_port,
                    boost::bind(&mac_controller_impl::handle_phy_msg, this, _1));

    }

    /*
     * Our virtual destructor.
     */
    mac_controller_impl::~mac_controller_impl()
    {
    }

    void
    mac_controller_impl::handle_llc_msg(pmt::pmt_t pdu)
    {
      auto meta = pmt::car(pdu);
      std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));

      meta = pmt::dict_add(meta, pmt::mp("dst_id"),
                           pmt::from_long(d_dst_id));
      meta = pmt::dict_add(meta, pmt::mp("src_id"),
                           pmt::from_long(d_src_id));
      meta = pmt::dict_add(meta, pmt::mp("sequence"),
                           pmt::from_long(d_tx_frame_counter));
      std::vector<uint8_t> header(4 + 8);
      header[0] = (uint8_t) d_dst_id;
      header[1] = (uint8_t) d_src_id;
      header[2] = (uint8_t) (d_tx_frame_counter >> 8) & 0xFF;
      header[3] = (uint8_t) d_tx_frame_counter & 0xFF;
      d_tx_frame_counter++;
      d_tx_frame_counter %= std::numeric_limits<uint16_t>::max();

      const auto since_epoch = std::chrono::high_resolution_clock::now().time_since_epoch();
      const uint64_t ticks = since_epoch.count();
      meta = pmt::dict_add(meta, pmt::mp("time"),
                           pmt::from_long(ticks));

      for(int i = 0; i < 8; ++i){
        header[i + 4] = (uint8_t) (ticks >> ((7 - i) * 8)) & 0xFF;
      }

      payload.insert(payload.begin(), header.begin(), header.end());

      uint16_t checksum = CRC::Calculate(payload.data(), payload.size(), CRC::CRC_16_XMODEM());
      payload.push_back((checksum >> 8) & 0xFF);
      payload.push_back(checksum & 0xFF);
      // GR_LOG_INFO(this->d_logger, checksum);
      auto pl = pmt::init_u8vector(payload.size(), payload);
      message_port_pub(d_phy_out_port, pmt::cons(meta, pl));

    }


    void
    mac_controller_impl::handle_phy_msg(pmt::pmt_t pdu)
    {
      auto meta = pmt::car(pdu);
      const std::vector<uint8_t> payload = pmt::u8vector_elements(pmt::cdr(pdu));

      const uint16_t rx_checksum = (uint16_t(payload[payload.size() - 2] << 8) |
                                    uint16_t(payload[payload.size() - 1]));

      const uint16_t checksum = CRC::Calculate(payload.data(), payload.size() - 2,
                                               CRC::CRC_16_XMODEM());
      // GR_LOG_INFO(this->d_logger, checksum);
      if(rx_checksum != checksum){
        GR_LOG_DEBUG(this->d_logger, "CRC16-XMODEM failed! calculated=" +
                                     std::to_string(checksum) +
                                     ", received=" +
                                     std::to_string(rx_checksum));
        return;
      }

      const unsigned dst = payload[0];
      const unsigned src = payload[1];
      const unsigned sequence = (uint16_t(payload[2] << 8) |
                                 uint16_t(payload[3]));

      if(dst != d_src_id || src != d_dst_id){
        std::string status("Drop packet!");

        if(dst == d_dst_id && src == d_src_id){
          status += " OWN packet!";
        }
        else{
          status += " WRONG address!";
        }
        status += " packet(dst=" +
                  std::to_string(dst) +
                  ", src=" +
                  std::to_string(src) +
                  ", sequence=" +
                  std::to_string(sequence) +
                  "), block(dst=" +
                  std::to_string(d_dst_id) +
                  ", src=" +
                  std::to_string(d_src_id) +
                  ")";

          GR_LOG_DEBUG(this->d_logger, status);

        return;
      }

      const std::vector<uint8_t> data(payload.begin() + 12,
                                      payload.end() - 2);

      meta = pmt::dict_add(meta, pmt::mp("dst_id"),
                           pmt::from_long(dst));
      meta = pmt::dict_add(meta, pmt::mp("src_id"),
                           pmt::from_long(src));
      meta = pmt::dict_add(meta, pmt::mp("sequence"),
                           pmt::from_long(sequence));
      const unsigned lost_packets = (sequence - d_rx_frame_counter - 1)
                                    % std::numeric_limits<uint16_t>::max();
      d_rx_frame_counter = sequence;
      meta = pmt::dict_add(meta, pmt::mp("lost_packets"),
                           pmt::from_long(lost_packets));

      uint64_t timestamp = 0;
      for(int i = 0; i < 8; ++i){
        timestamp |= uint64_t(payload[i + 4]) << ((7 - i) * 8);
      }
      meta = pmt::dict_add(meta, pmt::mp("time"),
                           pmt::from_long(timestamp));
      const auto since_epoch = std::chrono::high_resolution_clock::now().time_since_epoch();
      const uint64_t ticks = since_epoch.count();
      meta = pmt::dict_add(meta, pmt::mp("latency"),
                           pmt::from_long(ticks - timestamp));

      message_port_pub(d_llc_out_port,
                       pmt::cons(meta,
                                 pmt::init_u8vector(data.size(),
                                                    data)));
    }

    int
    mac_controller_impl::work(int noutput_items,
        gr_vector_const_void_star &input_items,
        gr_vector_void_star &output_items)
    {
      // This should never be called! This is a PDU only block!
      // Tell runtime system how many output items we produced.
      return noutput_items;
    }

  } /* namespace tacmac */
} /* namespace gr */

