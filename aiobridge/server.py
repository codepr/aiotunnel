import ssl
import uuid
import socket
import logging
import asyncio
from collections import namedtuple

from aiohttp import web

# Connection simple abstraction
Connection = namedtuple('Connection', ('transport', 'channel'))


class Channel:

    """Duplex communication channel, can be seen as a basic pipe, constituted by two asynchronous
    queue"""

    def __init__(self):
        self.req = asyncio.Queue()
        self.res = asyncio.Queue()

    async def push_request(self, request):
        return await self.req.put(request)

    async def push_response(self, response):
        return await self.res.put(response)

    async def pull_request(self):
        data = await self.req.get()
        self.req.task_done()
        return data

    async def pull_response(self):
        data = await self.res.get()
        self.res.task_done()
        return data


class TunnelProtocol(asyncio.Protocol):

    def __init__(self, loop, channel):
        self.loop = loop
        self.channel = channel
        self.transport = None
        self.logger = logging.getLogger('aiobridge.server.TunnelProtocol')
        self.peername = None

    def connection_made(self, transport):
        self.peername = peername = transport.get_extra_info('peername')
        self.logger.debug("Connection made with %s", peername)
        self.transport = transport
        sock = transport.get_extra_info('socket')
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.loop.create_task(self.async_consume_request())

    def data_received(self, data):
        self.loop.create_task(self.channel.push_response(data))

    def connection_lost(self, exc):
        self.logger.debug('The server closed the connection')
        self.transport.close()

    def eof_received(self):
        self.logger.debug('No more data to receive')
        self.transport.close()

    async def async_consume_request(self):
        while True:
            request = await self.channel.pull_request()
            await self.loop.run_in_executor(None, self.transport.write, request)


class Handler:

    def __init__(self, app):
        self.loop = app.loop
        self.tunnels = {}
        self.app = app
        self.app.add_routes([
            web.post('/aiobridge', self.post_aiobridge),
            web.put('/aiobridge/{cid}', self.put_aiobridge),
            web.get('/aiobridge/{cid}', self.get_aiobridge),
            web.delete('/aiobridge/{cid}', self.delete_aiobridge)
        ])
        self.logger = logging.getLogger('aiobridge.server.Handler')

    def close_all_tunnels(self):
        for _, conn in self.tunnels.items():
            conn.transport.close()

    async def push_request(self, cid, request):
        if cid not in self.tunnels:
            return
        return await self.tunnels[cid].channel.push_request(request)

    async def pull_response(self, cid):
        return await self.tunnels[cid].channel.pull_response()

    async def open_connection(self, host, port, channel):
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_connection(
            lambda: TunnelProtocol(loop, channel),
            host, port
        )
        return transport

    async def post_aiobridge(self, request):
        cid = uuid.uuid4()
        service = await request.text()
        channel = Channel()
        self.logger.debug("POST /aiobridge/%s HTTP/1.1 200", cid)
        host, port = service.split(':')
        transport = await self.open_connection(host, int(port), channel)
        self.tunnels[str(cid)] = Connection(transport, channel)
        return web.Response(text=str(cid))

    async def put_aiobridge(self, request):
        cid = request.match_info['cid']
        if cid not in self.tunnels:
            return web.Response()
        data = await request.read()
        self.logger.debug("PUT /aiobridge/%s HTTP/1.1 200 %s", cid, len(data))
        await self.push_request(cid, data)
        return web.Response()

    async def get_aiobridge(self, request):
        cid = request.match_info['cid']
        if cid not in self.tunnels:
            return web.Response()
        result = await self.pull_response(cid)
        self.logger.debug("GET /aiobridge/%s HTTP/1.1 200 %s", cid, len(result))
        return web.Response(body=result)

    async def delete_aiobridge(self, request):
        cid = request.match_info['cid']
        if cid not in self.tunnels:
            return web.Response()
        self.logger.debug("DELETE /aiobridge/%s HTTP/1.1 200")
        self.tunnels[cid].transport.close()
        del self.tunnels[cid]
        return web.Response()


def create_ssl_context(certfile, keyfile):
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile, keyfile)
    return ssl_context


def start(host, port, certfile=None, keyfile=None):
    app = web.Application()
    handler = Handler(app)
    try:
        if certfile and keyfile:
            ssl_context = create_ssl_context(certfile, keyfile)
            web.run_app(app, host=host, port=port, ssl_context=ssl_context)
        else:
            web.run_app(app, host=host, port=port)
    except KeyboardInterrupt:
        handler.close_all_tunnels()
        app.shutdown()
