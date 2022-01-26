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

#ifndef INCLUDED_TACMAC_TAG_TO_STREAM_VALUE_IMPL_H
#define INCLUDED_TACMAC_TAG_TO_STREAM_VALUE_IMPL_H

#include <tacmac/tag_to_stream_value.h>

namespace gr {
namespace tacmac {
template <class T>
class tag_to_stream_value_impl : public tag_to_stream_value<T>
{
private:
    const pmt::pmt_t d_key;
    const pmt::pmt_t d_dict_key;

    pmt::pmt_t get_tag_value(const tag_t& tag) const;

    T pmt_to_value(const pmt::pmt_t& info) const;


public:
    tag_to_stream_value_impl(size_t sizeof_stream_item, std::string key, std::string dict_key);
    ~tag_to_stream_value_impl();

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required);

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items);
};

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_TAG_TO_STREAM_VALUE_IMPL_H */
