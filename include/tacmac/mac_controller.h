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

#ifndef INCLUDED_TACMAC_MAC_CONTROLLER_H
#define INCLUDED_TACMAC_MAC_CONTROLLER_H

#include <tacmac/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
  namespace tacmac {

    /*!
     * \brief Accept PDUs, add/parse MAC header
     * \ingroup tacmac
     *
     */
    class TACMAC_API mac_controller : virtual public gr::sync_block
    {
     public:
      typedef boost::shared_ptr<mac_controller> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of tacmac::mac_controller.
       *
       * To avoid accidental use of raw pointers, tacmac::mac_controller's
       * constructor is in a private implementation
       * class. tacmac::mac_controller::make is the public interface for
       * creating new instances.
       */
      static sptr make(unsigned destination_id, unsigned source_id);
    };

  } // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_MAC_CONTROLLER_H */

