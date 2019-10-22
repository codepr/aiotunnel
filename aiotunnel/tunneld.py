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
import uuid
import logging
import asyncio
from functools import partial
from collections import namedtuple

from aiohttp import web

from . import CONFIG
from .protocol import TunnelProtocol


logger = logging.getLogger(__name__)

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


class Handler:

    def __init__(self, app, reverse=False):
        self.reverse = reverse
        self.conn = None
        self.tunnels = {}
        self.app = app
        self.app.add_routes([
            web.post('/aiotunnel', self.post_aiotunnel),
            web.put('/aiotunnel/{cid}', self.put_aiotunnel),
            web.get('/aiotunnel/{cid}', self.get_aiotunnel),
            web.delete('/aiotunnel/{cid}', self.delete_aiotunnel)
        ])
        self.logger = logging.getLogger('aiotunnel.tunneld.Handler')

    def close_all_tunnels(self):
        if self.conn:
            self.conn.close()
        for _, conn in self.tunnels.items():
            if conn.transport is not None:
                conn.transport.close()
        pending = asyncio.all_tasks()
        for task in pending:
            if not task.cancelled():
                task.cancel()

    async def push_request(self, cid, request):
        if cid not in self.tunnels:
            return
        return await self.tunnels[cid].channel.push_request(request)

    async def pull_response(self, cid):
        return await self.tunnels[cid].channel.pull_response()

    async def open_connection(self, host, port, channel):
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_connection(
            lambda: TunnelProtocol(channel),
            host, port
        )
        self.conn = protocol
        return transport

    async def create_endpoint(self, host, port, channel):
        # Get a reference to the event loop as we plan to use
        # low-level APIs.
        loop = asyncio.get_running_loop()
        server = await loop.create_server(
            lambda: TunnelProtocol(channel), host, port, reuse_port=True
        )
        self.conn = server
        async with server:
            await server.serve_forever()

    async def post_aiotunnel(self, request):
        cid = uuid.uuid4()
        service = await request.text()
        channel = Channel()
        host, port = service.split(':')
        if self.reverse:
            self.logger.info("Opening local port %s", port)
            loop = asyncio.get_running_loop()
            loop.create_task(self.create_endpoint(host, int(port), channel))
            self.tunnels[str(cid)] = Connection(None, channel)
        else:
            self.logger.info("Opening connection with %s:%s", host, port)
            transport = await self.open_connection(host, int(port), channel)
            self.tunnels[str(cid)] = Connection(transport, channel)
        return web.Response(text=str(cid))

    async def put_aiotunnel(self, request):
        cid = request.match_info['cid']
        if cid not in self.tunnels:
            return web.Response()
        data = await request.read()
        await self.push_request(cid, data)
        return web.Response()

    async def get_aiotunnel(self, request):
        cid = request.match_info['cid']
        if cid not in self.tunnels:
            return web.Response()
        result = await self.pull_response(cid)
        return web.Response(body=result)

    async def delete_aiotunnel(self, request):
        cid = request.match_info['cid']
        if cid not in self.tunnels:
            return web.Response()
        self.tunnels[cid].transport.close()
        del self.tunnels[cid]
        return web.Response()


def create_ssl_context(cafile, certfile, keyfile):
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile)
    ssl_context.load_cert_chain(certfile, keyfile)
    return ssl_context


async def on_shutdown_coro(app, handler):
    handler.close_all_tunnels()
    await app.shutdown()


def start_tunneld(host, port, reverse=False, cafile=None, certfile=None, keyfile=None):
    app = web.Application()
    handler = Handler(app, reverse)
    on_shutdown = partial(on_shutdown_coro, handler=handler)
    app.on_shutdown.append(on_shutdown)
    try:
        if cafile:
            ssl_context = create_ssl_context(cafile, certfile, keyfile)
            web.run_app(app, host=host, port=port, ssl_context=ssl_context, access_log=logger)
        else:
            web.run_app(app, host=host, port=port, access_log=logger,
                        access_log_format='"%r" %s %b %Tf %a - "%{User-agent}i"')
    except:
        if CONFIG['verbose']:
            logger.critical('Shutdown')
        else:
            logger.info("Shutdown")
