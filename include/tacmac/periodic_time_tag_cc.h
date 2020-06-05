/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TACMAC_PERIODIC_TIME_TAG_CC_H
#define INCLUDED_TACMAC_PERIODIC_TIME_TAG_CC_H

#include <tacmac/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
  namespace tacmac {

    /*!
     * \brief <+description of block+>
     * \ingroup tacmac
     *
     */
    class TACMAC_API periodic_time_tag_cc : virtual public gr::sync_block
    {
     public:
      typedef std::shared_ptr<periodic_time_tag_cc> sptr;

      /*!
       * \brief Return a shared_ptr to a new instance of tacmac::periodic_time_tag_cc.
       *
       * To avoid accidental use of raw pointers, tacmac::periodic_time_tag_cc's
       * constructor is in a private implementation
       * class. tacmac::periodic_time_tag_cc::make is the public interface for
       * creating new instances.
       */
      static sptr make(double samp_rate, uint32_t tag_interval);
    };

  } // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_PERIODIC_TIME_TAG_CC_H */
