/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TACMAC_TAGS_TO_MSG_DICT_H
#define INCLUDED_TACMAC_TAGS_TO_MSG_DICT_H

#include <gnuradio/sync_block.h>
#include <tacmac/api.h>

namespace gr {
namespace tacmac {

/*!
 * \brief Collect stream tags and output them as PMT message dicts.
 * \ingroup tacmac
 *
 */
class TACMAC_API tags_to_msg_dict : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<tags_to_msg_dict> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of tacmac::tags_to_msg_dict.
     *
     * To avoid accidental use of raw pointers, tacmac::tags_to_msg_dict's
     * constructor is in a private implementation
     * class. tacmac::tags_to_msg_dict::make is the public interface for
     * creating new instances.
     */
    static sptr make(size_t sizeof_stream_item);
};

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_TAGS_TO_MSG_DICT_H */
