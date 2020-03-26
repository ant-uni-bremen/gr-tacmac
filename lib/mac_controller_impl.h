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

#include <tacmac/mac_controller.h>

namespace gr {
  namespace tacmac {

    class mac_controller_impl : public mac_controller
    {
     private:
      unsigned d_dst_id;
      unsigned d_src_id;
      size_t d_tx_frame_counter;
      size_t d_rx_frame_counter;

      const pmt::pmt_t d_llc_in_port;
      const pmt::pmt_t d_llc_out_port;
      const pmt::pmt_t d_phy_in_port;
      const pmt::pmt_t d_phy_out_port;



     public:
      mac_controller_impl(unsigned destination_id, unsigned source_id);
      ~mac_controller_impl();

      // Where all the action really happens
      void handle_llc_msg(pmt::pmt_t pdu);
      void handle_phy_msg(pmt::pmt_t pdu);

      // Dummy!
      int work(
              int noutput_items,
              gr_vector_const_void_star &input_items,
              gr_vector_void_star &output_items
      );
    };

  } // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_MAC_CONTROLLER_IMPL_H */

