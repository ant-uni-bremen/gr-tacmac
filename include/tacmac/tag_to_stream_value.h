/* -*- c++ -*- */
/*
 * Copyright 2019 Johannes Demel.
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

#ifndef INCLUDED_TACMAC_TAG_TO_STREAM_VALUE_H
#define INCLUDED_TACMAC_TAG_TO_STREAM_VALUE_H

#include <gnuradio/block.h>
#include <tacmac/api.h>

namespace gr {
namespace tacmac {

/*!
 * \brief Grab tag value and put it on output stream
 * \ingroup tacmac
 *
 */
template <class T>
class TACMAC_API tag_to_stream_value : virtual public gr::block
{
public:
    typedef std::shared_ptr<tag_to_stream_value<T>> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of tacmac::tag_to_stream_value.
     *
     * To avoid accidental use of raw pointers, tacmac::tag_to_stream_value's
     * constructor is in a private implementation
     * class. tacmac::tag_to_stream_value::make is the public interface for
     * creating new instances.
     */
    static sptr make(size_t sizeof_stream_item, std::string key);
};
// typedef tag_to_stream_value<std::int16_t> tag_to_stream_value_ss;
typedef tag_to_stream_value<std::int32_t> tag_to_stream_value_ci;
typedef tag_to_stream_value<float> tag_to_stream_value_cf;
typedef tag_to_stream_value<gr_complex> tag_to_stream_value_cc;
} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_TAG_TO_STREAM_VALUE_H */
