#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Johannes Demel.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import pathlib
import yaml
from pathlib import Path
from pprint import pprint
import platform

try:
    # This should work in GR 3.10 at some point
    from gnuradio.uhd import find as uhd_find_devices
except ImportError:
    # This is for older GR versions. But causes issues with GR 3.10 (current main)
    from uhd import find as uhd_find_devices


def find_configuration_file(filename=None, search_path_root="."):
    if filename is not None:
        return filename
    files = list(pathlib.Path(search_path_root).glob("**/tacmac_configuration.yml"))
    if len(files) != 1:
        print(f"Warning: expected ONE configuration file, found: {len(files)}")
    if len(files) == 0:
        return ""
    return files[0]


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
    devices = uhd_find_devices(hint)
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
    configfilename = find_configuration_file()
    config = load_config_file(configfilename)["usrps"]
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


def remove_empty_kwargs(kwargs):
    keys = list(kwargs.keys())
    for k in keys:
        if not kwargs[k]:
            kwargs.pop(k)
    return kwargs


def load_single_device_config(config, devicename):
    device = config["usrps"].get(devicename, {"type": "b200"})
    device.update(config["usrp_defaults"][device["type"]])
    device_hint = f"type={device['type']}"
    if "serial" in device:
        device_hint = f"serial={device['serial']},type={device['type']}"
    found_devices = find_devices(device_hint)
    if found_devices:
        device.update(found_devices[0])
    device["usrp"] = device.get("name", devicename)
    return device


def load_device_config(config, devicename):
    devs = [load_single_device_config(config, d) for d in devicename]
    equal_keys = ["product", "type", "claimed", "fpga"]
    for ek in equal_keys:
        val = set([d.get(ek, "N/A") for d in devs])
        assert len(val) == 1

    device = {k: [d[k] for d in devs] for k in devs[0].keys()}
    result = {}
    for k, v in device.items():
        if len(set(v)) == 1:
            result[k] = list(set(v))[0]
        else:
            result[k] = v
    result.pop("primary_host", None)
    return result


def load_default_configuration(**kwargs):
    kwargs = remove_empty_kwargs(kwargs)
    fg_config = {}
    for k, v in kwargs.items():
        print(k, v)
    filename = kwargs.get("configuration_filename", None)
    filename = find_configuration_file(filename)
    config = load_config_file(filename)
    fg_config["hostname"] = hostname = kwargs.get("hostname", get_hostname())
    fg_config.update(config["flowgraph_defaults"])
    fg_config.update(config["database_defaults"])
    hostconfig = config["hosts"].get(hostname, {})

    fg_config["role"] = role = hostconfig.get("role", kwargs.get("role", "device"))
    fg_config.update(config["roles"][role])

    devicename = hostconfig.get("usrp", "N/A")

    device = load_device_config(config, devicename)
    fg_config.update(device)
    fg_config.update(hostconfig)
    fg_config.update(kwargs)
    return fg_config


def main():
    config = load_default_configuration(foo="bar", bla=None, fu="")
    pprint(config)
    return
    # config_file = find_configuration_file()
    # for f in config_file:
    #     print(f)
    # print(config_file)
    # return
    hostname = get_hostname()
    # pprint(config)

    # devices = find_devices()
    # devices = add_config_info(devices, config)
    # for d in devices:
    #     pprint(d)

    print(hostname)
    device = get_device()
    print(device)


if __name__ == "__main__":
    main()
