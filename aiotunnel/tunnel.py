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

import ssl
import asyncio
import logging

import aiohttp

from .protocol import LocalTunnelProtocol


logger = logging.getLogger(__name__)


async def create_endpoint(url, client_addr, target_addr, ssl_context=None):
    """Create a server endpoint TCP.

    Args:
    -----
    :type url: str
    :param url: The URL of the server part to communicate with using HTTP calls

    :type client_addr: tuple
    :param client_addr: A tuple (host, port) to expose a port on an address

    :type target_addr: tuple
    :param target_addr: A tuple (host, port) to expose a address:port on the server side in order to
                        let clients connection to the tunnel.
    """
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    host, port = client_addr
    target_host, target_port = target_addr
    remote_host = target_host + ':' + str(target_port)
    scheme = 'HTTPS' if ssl_context else 'HTTP'
    logger.info("Opening local port %s and %s:%s over %s", port, target_host, target_port, scheme)
    loop = asyncio.get_running_loop()
    # Start the server and serve forever
    server = await loop.create_server(
        lambda: LocalTunnelProtocol(remote_host, url, ssl_context),
        host, port
    )
    async with server:
        await server.serve_forever()


async def open_connection(url, client_addr, target_addr, ssl_context=None):
    """Open a TCP connection

    Args:
    -----
    :type url: str
    :param url: The URL of the server part to communicate with using HTTP calls

    :type client_addr: tuple
    :param client_addr: A tuple (host, port) to expose a port on an address

    :type target_addr: tuple
    :param target_addr: A tuple (host, port) to expose a address:port on the server side in order to
                        let clients connection to the tunnel.
    """

    remote = f'{client_addr[0]}:{client_addr[1]}'
    host, port = target_addr
    scheme = 'HTTPS' if ssl_context else 'HTTP'
    logger.info("Opening a connection with %s:%s and %s over %s", host, port, remote, scheme)
    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    transport, _ = await loop.create_connection(
        lambda: LocalTunnelProtocol(remote, url, on_con_lost, ssl_context),
        host, port
    )
    try:
        await on_con_lost
    finally:
        transport.close()


def start_tunnel(url, client_addr, target_addr,
                 reverse=False, cafile=None, certfile=None, keyfile=None):
    ssl_context = None
    if cafile:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH, cafile=cafile)
        ssl_context.load_cert_chain(certfile, keyfile)
    try:
        if not reverse:
            asyncio.run(create_endpoint(url, client_addr, target_addr, ssl_context))
        else:
            asyncio.run(open_connection(url, client_addr, target_addr, ssl_context))
    except:
        pass
