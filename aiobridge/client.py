import asyncio
import logging

import aiohttp

from .protocol import LocalTunnelProtocol


logger = logging.getLogger('aiobridge.client')


async def create_endpoint(url, client_addr, target_addr):
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    host, port = client_addr
    target_host, target_port = target_addr
    remote_host = target_host + ':' + str(target_port)
    logger.info("Opening local port 8888")
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        lambda: LocalTunnelProtocol(loop, remote_host, url),
        host, port
    )
    async with server:
        await server.serve_forever()


async def open_connection(url, client_addr, target_addr):
    remote = f'{client_addr[0]}:{client_addr[1]}'
    host, port = target_addr
    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    transport, _ = await loop.create_connection(
        lambda: LocalTunnelProtocol(loop, remote, url, on_con_lost),
        host, port
    )
    try:
        await on_con_lost
    finally:
        transport.close()


def start_client(url, client_addr, target_addr, reverse=False):
    print(url)
    if not reverse:
        asyncio.run(create_endpoint(url, client_addr, target_addr))
    else:
        asyncio.run(open_connection(url, client_addr, target_addr))
