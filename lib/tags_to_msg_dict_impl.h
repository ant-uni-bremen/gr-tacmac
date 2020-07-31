/* -*- c++ -*- */
/*
 * Copyright 2020 Johannes Demel.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_TACMAC_TAGS_TO_MSG_DICT_IMPL_H
#define INCLUDED_TACMAC_TAGS_TO_MSG_DICT_IMPL_H

#include <tacmac/tags_to_msg_dict.h>

namespace gr {
namespace tacmac {

class tags_to_msg_dict_impl : public tags_to_msg_dict
{
private:
    const pmt::pmt_t d_out_port = pmt::mp("out");

public:
    tags_to_msg_dict_impl(size_t sizeof_stream_item);
    ~tags_to_msg_dict_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

} // namespace tacmac
} // namespace gr

#endif /* INCLUDED_TACMAC_TAGS_TO_MSG_DICT_IMPL_H */
