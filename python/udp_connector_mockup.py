#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Johannes Demel.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
#

import argparse
import threading
import socket
import time
import random
import string
import select


class ApplicationThread(threading.Thread):
    """docstring for EchoClient"""

    def __init__(self, numclients, messagelength, portnumber,
                 timeout=None, strprefix='APP'):
        super().__init__()
        self.messagelength = messagelength
        self.numclients = numclients
        self.portnumber = portnumber
        self.strprefix = strprefix

        self.addresses = []
        if isinstance(portnumber, list):
            assert len(portnumber) == numclients
            for p in portnumber:
                self.addresses.append(('localhost', p))
        else:
            assert numclients > 0
            for i in range(numclients):
                p = portnumber + i
                self.addresses.append(('localhost', p))

        self.timeout = timeout
        self.socks = {}
        for a in self.addresses:
            self.socks[a] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socks[a].settimeout(self.timeout)

        self.choices = string.ascii_letters
        self.choices += string.digits
        self.choices += string.punctuation
        self.choices += ' '

    def generate_payload(self):
        msg_len = self.messagelength - len(self.strprefix)
        d = ''.join(random.choices(self.choices, k=msg_len))
        return d

    def handle_msg(self, data, server):
        rxprefix = data[0:3]
        payload = data[3:]
        print('received message: ', self.rx_string(rxprefix, payload, server))
        msg = self.get_message(payload)
        print('reply    message: ', self.rx_string(self.strprefix,
                                                   payload, server))
        self.send_reply(msg)

    def msg_string(self, counter, prefix, payload, address):
        s = 'SRC:[{}:{}]: '.format(address[0], address[1])
        s += '{:>6}'.format(counter)
        s += ': "{}":"{}"'.format(prefix, payload)
        return s

    def send_message(self, msg, address, sock):
        sent = sock.sendto(msg.encode(), address)
        assert sent == len(msg)

    def receive_message(self, sock):
        try:
            data, server = sock.recvfrom(4096)
            data = data.decode()
        except socket.timeout:
            data = ''
            server = ['', '']
            print('Client TIMEOUT! {}s'.format(sock.gettimeout()))
        return data, server

    def parse_message(self, data):
        plen = len(self.strprefix)
        prefix = data[0:plen]
        payload = data[plen:]
        return prefix, payload

    def get_message(self, payload):
        msg = self.strprefix + payload
        return msg


class EchoClientThread(ApplicationThread):
    """docstring for EchoClient"""

    def __init__(self, portnumber, strprefix='CLI'):
        super().__init__(1, 11, portnumber, None, strprefix)

        self.sock = self.socks[self.addresses[0]]
        self.sock.bind(self.addresses[0])
        self.rx_counter = 0

    def run(self):
        while True:
            data, server = self.receive_message(self.sock)
            rx_time = time.time()
            if len(data) < 1:
                continue
            msg = self.handle_msg(data, server)
            tx_time = time.time()
            self.send_message(msg, server, self.sock)
            print(self.rx_counter, '{:6.4f}ms'.format(
                1e3 * (tx_time - rx_time)))
            self.rx_counter += 1

    def handle_msg(self, data, server):
        rxprefix, payload = self.parse_message(data)
        print('received message: ', self.msg_string(self.rx_counter,
                                                    rxprefix,
                                                    payload, server))
        msg = self.get_message(payload)
        print('reply    message: ', self.msg_string(self.rx_counter,
                                                    self.strprefix,
                                                    payload, server))
        return msg


class AppServerThread(ApplicationThread):
    def __init__(self, numclients, messagelength, portnumber,
                 timeout=1e-2, strprefix='APP'):
        super().__init__(numclients, messagelength, portnumber,
                         timeout, strprefix)
        self.tx_counter = 0

    def run(self):
        while True:
            self.produce_messages()
            self.tx_counter += 1
            time.sleep(.1)
            self.flush()

    def flush(self):
        # make sure we empty receive buffers.
        r, w, e = select.select(self.socks.values(), [], [], 0.0)
        for sr in r:
            d, s = sr.recvfrom(4096)
            d = d.decode()
            rxprefix, rxpayload = self.parse_message(d)
            print('FLUSH message:', self.msg_string(self.tx_counter - 1,
                                                    rxprefix, rxpayload,
                                                    s), '\tLOST')

    def produce_messages(self):
        for a in self.addresses:
            self.send_message_to_client(a)

    def send_message_to_client(self, address):
        sock = self.socks[address]
        payload = self.generate_payload()
        msg = self.get_message(payload)
        print('Send  message:', self.msg_string(self.tx_counter,
                                                self.strprefix,
                                                payload, address))
        tx_time = time.time()
        self.send_message(msg, address, sock)
        data, server = self.receive_message(sock)
        rx_time = time.time()
        rtt = rx_time - tx_time
        rtt_str = '{:6.4f}ms'.format(rtt * 1e3)
        if len(data) > 0:
            rxprefix, rxpayload = self.parse_message(data)
            print('Reply message:', self.msg_string(self.tx_counter,
                                                    rxprefix, rxpayload,
                                                    server),
                  '\tRTT:', rtt_str)
            assert rxpayload == payload


def main():
    parser = argparse.ArgumentParser(description='TACNET Application mockup')
    parser.add_argument('-r', '--role', type=str, nargs='?',
                        default='server',
                        choices=['server', 'client'],
                        help='Choose role')

    parser.add_argument('-p', '--portnumber', type=int, nargs='*',
                        default=52001,
                        help='Choose UDP portnumber')
    parser.add_argument('-l', '--messagelength', type=int, nargs='?',
                        default=11,
                        help='Message length in bytes')
    parser.add_argument('-t', '--timeout', type=float, nargs='?',
                        default=1e-2,
                        help='Server response wait timeout')
    parser.add_argument('-c', '--numclients', type=int, nargs='?',
                        default=1,
                        help='Choose # clients')
    parser.add_argument('-s', '--strprefix', type=str, nargs='?',
                        default='MOF',
                        help='Transmit string prefix for identification purposes')
    args = parser.parse_args()
    print(args)
    if args.role == 'server':
        runningThread = AppServerThread(args.numclients,
                                        args.messagelength,
                                        args.portnumber,
                                        args.timeout, args.strprefix)
    elif args.role == 'client':
        assert args.numclients == 1
        runningThread = EchoClientThread(args.portnumber, args.strprefix)
    else:
        raise Exception('Whatever role! Specify "client" or "server"!')
    runningThread.start()


if __name__ == '__main__':
    main()
