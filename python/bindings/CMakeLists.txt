# Copyright 2020 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

GR_PYTHON_CHECK_MODULE_RAW(
    "pygccxml"
    "import pygccxml"
    PYGCCXML_FOUND
    )

include(GrPybind)

########################################################################
# Python Bindings
########################################################################

list(APPEND tacmac_python_files
    mac_controller_python.cc
    periodic_time_tag_cc_python.cc
    tag_to_stream_value_python.cc
    status_collector_python.cc
    tags_to_msg_dict_python.cc python_bindings.cc)

GR_PYBIND_MAKE_OOT(tacmac
   ../..
   gr::tacmac
   "${tacmac_python_files}")

install(TARGETS tacmac_python DESTINATION ${GR_PYTHON_DIR}/tacmac COMPONENT pythonapi)
