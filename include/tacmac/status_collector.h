/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TACMAC_STATUS_COLLECTOR_H
#define INCLUDED_TACMAC_STATUS_COLLECTOR_H

#include <gnuradio/sync_block.h>
#include <tacmac/api.h>

namespace gr {
namespace tacmac {

/*!
 * \brief <+description of block+>
 * \ingroup tacmac
 *
 */
class TACMAC_API status_collector : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<status_collector> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of tacmac::status_collector.
     *
     * To avoid accidental use of raw pointers, tacmac::status_collector's
     * constructor is in a private implementation
     * class. tacmac::status_collector::make is the public interface for
     * creating new instances.
     */
    static sptr make();
};

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_STATUS_COLLECTOR_H */
