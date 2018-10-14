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


def get_parser():
    parser = argparse.ArgumentParser(description='aiotunnel CLI aiotunnels')
    parser.add_argument('subcommand')
    parser.add_argument('--reverse', '-r', action='store_true')
    parser.add_argument('--client', '-c', action='store_true')
    parser.add_argument('--bridge', '-b', action='store')
    parser.add_argument('--addr', '-a', action='store')
    parser.add_argument('--port', '-p', action='store')
    parser.add_argument('--target-addr', '-A', action='store')
    parser.add_argument('--target-port', '-P', action='store')
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    client_host, client_port = '0.0.0.0', 8888
    server_host, server_port = '0.0.0.0', 8080
    reverse = args.reverse or False
    url = f'http://{server_host}:{server_port}/aiotunnel'

    if args.subcommand == 'client':
        if args.target_port:
            target_port = int(args.target_port)
        if args.target_addr:
            target_addr = args.target_addr
        if args.addr:
            client_host = args.addr
        if args.port:
            client_port = args.port
        start_tunnel(url, (client_host, client_port), (target_addr, target_port), reverse)
    else:
        if args.addr:
            server_host = args.addr
        if args.port:
            server_port = args.port
        start_tunneld(server_host, server_port, reverse)
