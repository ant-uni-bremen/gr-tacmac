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
/* BINDTOOL_HEADER_FILE(status_collector.h)                                        */
/* BINDTOOL_HEADER_FILE_HASH(3a330f535c9ace7307d97366eeaa1900)                     */
/***********************************************************************************/

#include <pybind11/complex.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include <tacmac/status_collector.h>
// pydoc.h is automatically generated in the build directory
#include <status_collector_pydoc.h>

void bind_status_collector(py::module& m)
{

    using status_collector = gr::tacmac::status_collector;


    py::class_<status_collector,
               gr::sync_block,
               gr::block,
               gr::basic_block,
               std::shared_ptr<status_collector>>(
        m, "status_collector", D(status_collector))

        .def(py::init(&status_collector::make), D(status_collector, make))


        ;
}
