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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include "tag_to_stream_value_impl.h"
#include <gnuradio/io_signature.h>

#include <type_traits>

namespace gr {
namespace tacmac {

template <class T>
typename tag_to_stream_value<T>::sptr
tag_to_stream_value<T>::make(size_t sizeof_stream_item, std::string key)
{
    return gnuradio::get_initial_sptr(
        new tag_to_stream_value_impl<T>(sizeof_stream_item, key));
}


/*
 * The private constructor
 */
template <class T>
tag_to_stream_value_impl<T>::tag_to_stream_value_impl(size_t sizeof_stream_item,
                                                      std::string key)
    : gr::block("tag_to_stream_value",
                gr::io_signature::make(1, 1, sizeof_stream_item),
                gr::io_signature::make(1, 1, sizeof(T))),
      d_key(pmt::intern(key))
{
    this->set_tag_propagation_policy(gr::block::TPP_DONT);
}

/*
 * Our virtual destructor.
 */
template <class T>
tag_to_stream_value_impl<T>::~tag_to_stream_value_impl()
{
}

template <class T>
void tag_to_stream_value_impl<T>::forecast(int noutput_items,
                                           gr_vector_int& ninput_items_required)
{
    ninput_items_required[0] = noutput_items;
    // for(int i = 0; i < ninput_items_required.size(); ++i){
    //   ninput_items_required[i] = noutput_items;
    // }
}

template <class T>
pmt::pmt_t tag_to_stream_value_impl<T>::get_tag_value(const tag_t& tag) const
{
    // pmt::pmt_t info = tag.value;
    if (!pmt::is_dict(tag.value)) {
        return tag.value;
    } else {
        return pmt::dict_ref(tag.value, d_key, pmt::PMT_NIL);
    }
}

template <>
gr_complex
tag_to_stream_value_impl<gr_complex>::pmt_to_value(const pmt::pmt_t& info) const
{
    return gr_complex(pmt::to_complex(info));
}

template <>
float tag_to_stream_value_impl<float>::pmt_to_value(const pmt::pmt_t& info) const
{
    return float(pmt::to_float(info));
}

template <>
std::int32_t
tag_to_stream_value_impl<std::int32_t>::pmt_to_value(const pmt::pmt_t& info) const
{
    if (pmt::is_uint64(info)) {
        return std::int32_t(pmt::to_uint64(info));

    } else if (pmt::is_integer(info)) {
        return std::int32_t(pmt::to_long(info));
    } else {
        return 0;
    }
}

template <class T>
int tag_to_stream_value_impl<T>::general_work(int noutput_items,
                                              gr_vector_int& ninput_items,
                                              gr_vector_const_void_star& input_items,
                                              gr_vector_void_star& output_items)
{
    T* out = (T*)output_items[0];

    const int consumed_items = std::min(noutput_items, ninput_items[0]);

    const uint64_t tag_reg_start = gr::block::nitems_read(0);
    const uint64_t tag_reg_end = tag_reg_start + consumed_items;

    std::vector<tag_t> tags;
    gr::block::get_tags_in_range(tags, 0, tag_reg_start, tag_reg_end, d_key);

    int produced_items = 0;
    for (const tag_t& tag : tags) {
        auto info = get_tag_value(tag);

        if (pmt::is_uniform_vector(info)) {
            if constexpr (std::is_integral_v<T>) {
                if (pmt::is_s32vector(info)) {
                    auto vec = pmt::s32vector_elements(info);
                    if (produced_items + vec.size() > noutput_items) {
                        break;
                    }
                    memcpy(out, vec.data(), sizeof(T) * vec.size());
                    produced_items += vec.size();
                }
            } else if (std::is_floating_point_v<T>) {
                if (pmt::is_f32vector(info)) {
                    auto vec = pmt::f32vector_elements(info);
                    if (produced_items + vec.size() > noutput_items) {
                        break;
                    }
                    memcpy(out, vec.data(), sizeof(T) * vec.size());
                    produced_items += vec.size();
                }
            } else {
                if (pmt::is_c32vector(info)) {
                    auto vec = pmt::c32vector_elements(info);
                    if (produced_items + vec.size() > noutput_items) {
                        break;
                    }
                    memcpy(out, vec.data(), sizeof(T) * vec.size());
                    produced_items += vec.size();
                }
            }
        } else {
            out[produced_items] = pmt_to_value(info);
            produced_items++;
        }

        if (produced_items >= noutput_items) {
            break;
        }
    }

    // Tell runtime system how many input items we consumed on
    // each input stream.
    gr::block::consume_each(consumed_items);

    // Tell runtime system how many output items we produced.
    return produced_items;
}

template class tag_to_stream_value<std::int32_t>;
template class tag_to_stream_value<float>;
template class tag_to_stream_value<gr_complex>;
} /* namespace tacmac */
} /* namespace gr */
