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

#include <gnuradio/sync_block.h>
#include <tacmac/api.h>

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
    typedef std::shared_ptr<mac_controller> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of tacmac::mac_controller.
     *
     * To avoid accidental use of raw pointers, tacmac::mac_controller's
     * constructor is in a private implementation
     * class. tacmac::mac_controller::make is the public interface for
     * creating new instances.
     */
    static sptr make(unsigned destination_id, unsigned source_id, unsigned mtu_size);

    virtual void activate_replay_mode(bool activate) = 0;
    virtual bool replay_mode() = 0;
};

/*!
 * \brief Calculate CRC checksum
 * \ingroup tacmac
 *
 * This function calculates the 16bit CRC checksum according to the algorithm that is used
 * in this implementation.
 */
uint16_t TACMAC_API calculate_checksum(const std::vector<uint8_t>& payload,
                                       unsigned num_ignored_tail_bytes = 0);

/*!
 * \brief Parse payload with header
 * \ingroup tacmac
 *
 * Parses the header that is defined in this MAC controller.
 */
std::tuple<unsigned, unsigned, unsigned, unsigned, uint16_t>
    TACMAC_API parse_payload(const std::vector<uint8_t>& payload);

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_MAC_CONTROLLER_H */
