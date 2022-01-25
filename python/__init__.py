#
# Copyright 2008,2009 Free Software Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

# The presence of this file turns this directory into a Python package

'''
This is the GNU Radio TACMAC module. Place your Python package
description here (python/__init__.py).
'''
from __future__ import unicode_literals
import os

# import pybind11 generated symbols into the tacmac namespace
try:
    from .tacmac_python import *
except ImportError:
    dirname, filename = os.path.split(os.path.abspath(__file__))
    __path__.append(os.path.join(dirname, "bindings"))
    from .tacmac_python import *

# import any pure python here
from .udp_interface import udp_interface
from .elasticsearch_connector import elasticsearch_connector
from .phy_transmitter import phy_transmitter
from .lower_phy_receiver import lower_phy_receiver
from .phy_layer import phy_layer
from .uhd_configuration import get_device, load_default_configuration
#
