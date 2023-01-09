#!/bin/bash

# We already saw a lot of values...
#sysctl -w net.core.rmem_max=326086956
#sysctl -w net.core.rmem_max=791304326
#sysctl -w net.core.wmem_max=24266666

# This is the N310 w/ UHD 3.15 config
sysctl -w net.core.wmem_max=62500000
sysctl -w net.core.rmem_max=62500000
