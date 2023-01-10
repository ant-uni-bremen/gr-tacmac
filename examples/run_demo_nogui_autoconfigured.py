#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: GPL-3.0
#
# Title: GFDM over-the-air demo headless
# Author: Johannes Demel
# GNU Radio version: 3.9.5.0

from tacmac import load_default_configuration
from argparse import Namespace
from gfdm_ota_demo_nogui import argument_parser
from gfdm_ota_demo_nogui import main as fg_main


def main():
    args = argument_parser().parse_args()

    config = load_default_configuration()
    options = Namespace()
    d = vars(options)
    d.update(config)
    if "addr" in d and isinstance(d["addr"], list):
        d["rx_addr"] = ",".join([f"addr{i}={v}" for i, v in enumerate(d["addr"])])
    else:
        d["rx_addr"] = f"serial={d['serial']}"
    d["tx_addr"] = d["rx_addr"]

    for k in vars(args).keys():
        if k not in d:
            print("missing", k)

    fg_main(options=options)


if __name__ == "__main__":
    main()
