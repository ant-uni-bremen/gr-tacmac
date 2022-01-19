#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import pathlib
import uhd

import yaml
from pathlib import Path
from pprint import pprint
import platform


def validate_config_file(filename):
    config_locs = ["python", ".", pathlib.Path(__file__).parent]
    for loc in config_locs:
        p = Path(loc, filename)
        # print(p)
        if p.is_file():
            return p
    raise RuntimeError(f"Invalid Config file {filename}!")


def load_config_file(filename):
    print(f'Loading UHD configuration from "{filename}" ..."')
    filename = validate_config_file(filename)
    with open(filename) as file:
        fileconfig = yaml.safe_load(file)
        return fileconfig


def get_hostname():
    return platform.uname().node


def find_devices(hint=""):
    devices = uhd.find(hint)
    return [d.to_dict() for d in devices]


def filter_devices(devices):
    results = []
    for d in devices:
        if d["type"] in ("b200",):
            # we add more types here if necessary.
            # USB devices are only connected to one host!
            results.append(d)
        elif d.get("claimed", False):
            continue
        else:
            results.append(d)
    return results


def add_config_info(devices, config):
    results = []
    for d in devices:
        serial = d["serial"]
        for k, v in config.items():
            if v["serial"] == serial:
                d["name"] = k
                assert d["type"] == v["type"]
                assert d["product"] == v["product"]
                d["primary_host"] = v["primary_host"]
        results.append(d)
    return results


def find_primary_device(devices):
    hostname = get_hostname()
    for d in devices:
        if d.get("primary_host", "") == hostname:
            return d
    return None


def find_usb_device(devices):
    for d in devices:
        if d["type"] in ("b200",):
            # We assume there's a maximum of one USB device per host.
            return d
    return None


def get_device(hint=""):
    devices = find_devices(hint)
    config = load_config_file("usrp_info.yml")
    devices = add_config_info(devices, config)
    # pprint(devices)
    if len(devices) == 1:
        return devices[0]
    primary_device = find_primary_device(devices)
    if primary_device:
        return primary_device
    usb_device = find_usb_device(devices)
    if usb_device:
        return usb_device


def main():
    hostname = get_hostname()
    config = load_config_file("usrp_info.yml")
    pprint(config)

    # devices = find_devices()
    # devices = add_config_info(devices, config)
    # for d in devices:
    #     pprint(d)

    print(hostname)
    device = get_device()
    print(device)


if __name__ == "__main__":
    main()
