from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
from .server import start_server
from .client import start_client


def get_parser():
    parser = argparse.ArgumentParser(description='Aiobridge CLI aiobridges')
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
    url = f'http://{server_host}:{server_port}/aiobridge'

    if args.subcommand == 'client':
        if args.target_port:
            target_port = int(args.target_port)
        if args.target_addr:
            target_addr = args.target_addr
        if args.addr:
            client_host = args.addr
        if args.port:
            client_port = args.port
        start_client(url, (client_host, client_port), (target_addr, target_port), reverse)
    else:
        if args.addr:
            server_host = args.addr
        if args.port:
            server_port = args.port
        start_server(server_host, server_port, reverse)
