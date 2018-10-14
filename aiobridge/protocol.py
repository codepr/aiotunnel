import socket
import asyncio
import logging

import aiohttp


class BaseTunnelProtocol(asyncio.Protocol):

    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.logger = logging.getLogger('aiobridge.protocol.BaseTunnelProtocol')

    def connection_made(self, transport):
        self.transport = transport
        self.transport.set_write_buffer_limits(0)
        sock = transport.get_extra_info('socket')
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def connection_lost(self, exc):
        self.logger.debug('The server closed the connection')
        self.transport.close()

    def eof_received(self):
        self.logger.debug('No more data to receive')
        self.transport.close()


class TunnelProtocol(BaseTunnelProtocol):

    def __init__(self, loop, channel):
        self.channel = channel
        self.logger = logging.getLogger('aiobridge.protocol.TunnelProtocol')
        super().__init__(loop)

    def connection_made(self, transport):
        super().connection_made(transport)
        self.loop.create_task(self.async_consume_request())

    def data_received(self, data):
        self.loop.create_task(self.channel.push_response(data))

    async def async_consume_request(self):
        while True:
            request = await self.channel.pull_request()
            await self.loop.run_in_executor(None, self.transport.write, request)


class LocalTunnelProtocol(BaseTunnelProtocol):

    def __init__(self, loop, remote_host, url, on_conn_lost=None):
        self.cid = None
        self.url = url
        self.remote_host = remote_host
        self.write_queue = asyncio.Queue()
        self.on_conn_lost = on_conn_lost
        self.logger = logging.getLogger('aiobridge.protocol.LocalTunnelProtocol')
        super().__init__(loop)

    def connection_made(self, transport):
        super().connection_made(transport)
        self.loop.create_task(self.async_open_remote_connection())

    def data_received(self, data):
        self.loop.create_task(self.write_queue.put(data))

    def eof_received(self):
        self.loop.create_task(self.async_close_remote_connection())
        if self.on_conn_lost:
            self.on_conn_lost.set_result(True)
        super().eof_received()

    async def async_open_remote_connection(self):
        remote = self.remote_host.encode()
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, data=remote) as resp:
                cid = await resp.text()
        self.cid = cid
        self.logger.info("%s over HTTP to %s", self.remote_host, self.url)
        self.logger.info("Obtained a client id: %s", cid)
        self.loop.create_task(self.async_write_data())
        self.loop.create_task(self.async_read_data())

    async def async_close_remote_connection(self):
        async with aiohttp.ClientSession() as session:
            await session.delete(f'{self.url}/{self.cid}')

    async def async_write_data(self):
        while True:
            data = await self.write_queue.get()
            async with aiohttp.ClientSession() as session:
                await session.put(f'{self.url}/{self.cid}', data=data)

    async def async_read_data(self):
        while True:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.url}/{self.cid}') as resp:
                    data = await resp.read()
                    self.transport.write(data)
