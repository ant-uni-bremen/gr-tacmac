/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "tags_to_msg_dict_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace tacmac {

tags_to_msg_dict::sptr tags_to_msg_dict::make(size_t sizeof_stream_item)
{
    return gnuradio::make_block_sptr<tags_to_msg_dict_impl>(sizeof_stream_item);
}


/*
 * The private constructor
 */
tags_to_msg_dict_impl::tags_to_msg_dict_impl(size_t sizeof_stream_item)
    : gr::sync_block("tags_to_msg_dict",
                     gr::io_signature::make(1, 1, sizeof_stream_item),
                     gr::io_signature::make(0, 0, 0))
{
    message_port_register_out(d_out_port);
}

/*
 * Our virtual destructor.
 */
tags_to_msg_dict_impl::~tags_to_msg_dict_impl() {}

int tags_to_msg_dict_impl::work(int noutput_items,
                                gr_vector_const_void_star& input_items,
                                gr_vector_void_star& output_items)
{
    const uint64_t tag_reg_start = nitems_read(0);
    const uint64_t tag_reg_end = tag_reg_start + noutput_items;

    std::vector<tag_t> tags;
    gr::block::get_tags_in_range(tags, 0, tag_reg_start, tag_reg_end);
    if (tags.size() < 1) {
        return noutput_items;
    }
    std::sort(tags.begin(), tags.end(), &gr::tag_t::offset_compare);

    pmt::pmt_t current_msg = pmt::make_dict();
    uint64_t offset = tags[0].offset;
    for (const auto& tag : tags) {
        if (tag.offset > offset) {
            message_port_pub(d_out_port, current_msg);
            current_msg = pmt::make_dict();
            offset = tag.offset;
        }
        current_msg = pmt::dict_add(current_msg, tag.key, tag.value);
    }

    if (pmt::length(current_msg) > 0) {
        message_port_pub(d_out_port, current_msg);
    }

    // Tell runtime system how many output items we produced.
    return noutput_items;
}

} /* namespace tacmac */
} /* namespace gr */
