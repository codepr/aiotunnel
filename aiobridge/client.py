import asyncio
import logging
import threading

import aiohttp


logger = logging.getLogger('aiobridge.client')


class LocalServerProtocol(asyncio.Protocol):

    def __init__(self, loop, remote_host):
        self.transport = None
        self.cid = None
        self.loop = loop
        self.remote_host = remote_host
        self.conn_event = threading.Event()
        self.write_queue = asyncio.Queue()
        self.logger = logging.getLogger('aiobridge.client.LocalServerProtocol')
        self.peername = None

    def connection_made(self, transport):
        self.peername = peername = transport.get_extra_info('peername')
        self.logger.info('Connection from %s', peername)
        self.transport = transport
        self.transport.set_write_buffer_limits(0)
        self.loop.create_task(self.async_open_remote_connection())

    def data_received(self, data):
        self.logger.debug('Data received from %s: %s', self.peername, data)
        self.loop.create_task(self.write_queue.put(data))

    def eof_received(self):
        self.logger.info("Closed connection")
        self.loop.create_task(self.async_close_remote_connection())
        self.transport.close()

    async def async_open_remote_connection(self):
        remote = self.remote_host.encode()
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:8080/aiobridge', data=remote) as resp:
                cid = await resp.text()
        self.cid = cid
        logger.info("Registered %s over HTTP to http://localhost:8080/aiobridge", self.remote_host)
        logger.info("Obtained a client id: %s", cid)
        self.loop.create_task(self.async_write_data())
        self.loop.create_task(self.async_read_data())

    async def async_close_remote_connection(self):
        async with aiohttp.ClientSession() as session:
            await session.delete(f'http://localhost:8080/aiobridge/{self.cid}')

    async def async_write_data(self):
        while True:
            data = await self.write_queue.get()
            async with aiohttp.ClientSession() as session:
                await session.put(f'http://localhost:8080/aiobridge/{self.cid}', data=data)

    async def async_read_data(self):
        while True:
            async with aiohttp.ClientSession() as session:
                async with await session.get(f'http://localhost:8080/aiobridge/{self.cid}') as resp:
                    data = await resp.read()
                    self.transport.write(data)


async def main(host, port, target_host, target_port):
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    remote_host = target_host + ':' + str(target_port)
    logger.info("Opening local port 8888")
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        lambda: LocalServerProtocol(loop, remote_host),
        host, port
    )
    async with server:
        await server.serve_forever()


def run_client(client_host, client_port, target_host, target_port):
    asyncio.run(main(client_host, client_port, target_host, target_port))
