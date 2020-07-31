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
/* BINDTOOL_HEADER_FILE(tags_to_msg_dict.h)                                        */
/* BINDTOOL_HEADER_FILE_HASH(bcc14990ef0b1f8f7bbf15f4306e8c6f)                     */
/***********************************************************************************/

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include <tacmac/tags_to_msg_dict.h>
// pydoc.h is automatically generated in the build directory
#include <tags_to_msg_dict_pydoc.h>

void bind_tags_to_msg_dict(py::module& m)
{

    using tags_to_msg_dict    = gr::tacmac::tags_to_msg_dict;


    py::class_<tags_to_msg_dict, gr::sync_block, gr::block, gr::basic_block,
        std::shared_ptr<tags_to_msg_dict>>(m, "tags_to_msg_dict", D(tags_to_msg_dict))

        .def(py::init(&tags_to_msg_dict::make),
           D(tags_to_msg_dict,make)
        )
        



        ;




}







