/*
 * Copyright 2020 Free Software Foundation, Inc.
 *
 * This file is part of GNU Radio
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 */

/***********************************************************************************/
/* This file is automatically generated using bindtool and can be manually edited  */
/* The following lines can be configured to regenerate this file during cmake      */
/* If manual edits are made, the following tags should be modified accordingly.    */
/* BINDTOOL_GEN_AUTOMATIC(0)                                                       */
/* BINDTOOL_USE_PYGCCXML(0)                                                        */
/* BINDTOOL_HEADER_FILE(tag_to_stream_value.h)                                     */
/* BINDTOOL_HEADER_FILE_HASH(603645e3548ee851d9f64b13771d21c0)                     */
/***********************************************************************************/

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include <tacmac/tag_to_stream_value.h>
// pydoc.h is automatically generated in the build directory
#include <tag_to_stream_value_pydoc.h>


template <typename T>
void bind_tag_to_stream_value_template(py::module& m, const char* classname)
{
    using tag_to_stream_value = gr::tacmac::tag_to_stream_value<T>;

    py::class_<tag_to_stream_value,
               gr::block,
               gr::basic_block,
               std::shared_ptr<tag_to_stream_value>>(m, classname)
        .def(py::init(&gr::tacmac::tag_to_stream_value<T>::make),
             py::arg("sizeof_stream_item"),
             py::arg("key"),
             py::arg("dict_key"));
}

void bind_tag_to_stream_value(py::module& m)
{
    bind_tag_to_stream_value_template<std::int32_t>(m, "tag_to_stream_value_ci");
    bind_tag_to_stream_value_template<float>(m, "tag_to_stream_value_cf");
    bind_tag_to_stream_value_template<gr_complex>(m, "tag_to_stream_value_cc");
}
