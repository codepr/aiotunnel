# BSD 3-Clause License
#
# Copyright (c) 2018, Andrea Giacomo Baldan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
from .tunnel import start_tunnel
from .tunneld import start_tunneld
from . import CONFIG, read_configuration, set_config_key, setup_logging


def get_parser():
    parser = argparse.ArgumentParser(description='aiotunnel CLI aiotunnels')
    parser.add_argument('subcommand', help='Runtime mode, can be either client or server')
    parser.add_argument('--file', '-f', nargs='?',
                        type=argparse.FileType('r'), help='Configuration file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        default=False, help='Run with more logs')
    parser.add_argument('--reverse', '-r', action='store_true',
                        help='Run in reverse mode e.g. client connect to the '
                        'service to expose and ask the server to open a port')
    parser.add_argument('--client', '-c', action='store_true', help='Run in client mode')
    parser.add_argument('--addr', '-a', action='store', help='Set address to listen to')
    parser.add_argument('--port', '-p', action='store', help='Set the port to open')
    parser.add_argument('--target-addr', '-A', action='store', help='Set the target to expose/reach')
    parser.add_argument('--target-port', '-P', action='store', help='Set the port for target-addr')
    parser.add_argument('--server-addr', '-sa', action='store', help='Set the target address')
    parser.add_argument('--server-port', '-sp', action='store', help='Set the target port')
    parser.add_argument('--ca', action='store', help='Set the cert. authority file')
    parser.add_argument('--cert', action='store', help='Set the crt file for SSL/TLS encryption')
    parser.add_argument('--key', action='store', help='Set the key file for SSL/TLS encryption')
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if args.file:
        config_file = args.file
        read_configuration(config_file)

    if args.verbose:
        set_config_key('verbose', args.verbose)
        set_config_key('loglevel', 'DEBUG')

    setup_logging()

    # SSL/TLS certificates
    cafile = args.ca
    certfile = args.cert
    keyfile = args.key

    if cafile or (certfile and keyfile):
        set_config_key('client', {'server_port': 8443})
        set_config_key('server', {'port': 8443})

    # Connection directives, addresses and targets
    client_host, client_port = CONFIG['client']['host'], CONFIG['client']['port']
    server_host, server_port = CONFIG['server']['host'], CONFIG['server']['port']
    reverse = args.reverse or CONFIG.get('reverse', False)

    if args.subcommand == 'client':
        if args.target_port:
            target_port = int(args.target_port)
            set_config_key('client', {'target_port': target_port})
        if args.target_addr:
            target_addr = args.target_addr
            set_config_key('client', {'target_host': target_addr})
        if args.addr:
            client_host = args.addr
            set_config_key('client', {'host': client_host})
        if args.port:
            client_port = args.port
            set_config_key('client', {'port': client_port})
        if args.server_addr:
            server_host = args.server_addr
            set_config_key('server', {'host': server_host})
        if args.server_port:
            server_port = args.server_port
            set_config_key('server', {'port': server_port})
        scheme = 'https' if cafile else 'http'
        url = f'{scheme}://{server_host}:{server_port}/aiotunnel'
        start_tunnel(url, (client_host, client_port), (target_addr, target_port),
                     reverse, cafile=cafile, certfile=certfile, keyfile=keyfile)
    else:
        if args.addr:
            server_host = args.addr
            set_config_key('server', {'host': server_host})
        if args.port:
            server_port = args.port
            set_config_key('server', {'port': server_port})
        start_tunneld(server_host, server_port, reverse,
                      cafile=cafile, certfile=certfile, keyfile=keyfile)
