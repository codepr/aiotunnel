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

import socket
import asyncio
import logging

import aiohttp


class BaseTunnelProtocol(asyncio.Protocol):

    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.transport = None
        self._shutdown = asyncio.Event()
        self.logger = logging.getLogger('aiotunnel.protocol.BaseTunnelProtocol')

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

    def close(self):
        self._shutdown.set()


class TunnelProtocol(BaseTunnelProtocol):

    def __init__(self, channel):
        self.channel = channel
        self.logger = logging.getLogger('aiotunnel.protocol.TunnelProtocol')
        super().__init__()

    def connection_made(self, transport):
        super().connection_made(transport)
        self.loop.create_task(self.async_consume_request())

    def data_received(self, data):
        self.loop.create_task(self.channel.push_response(data))

    async def async_consume_request(self):
        while not self._shutdown.is_set():
            try:
                request = await self.channel.pull_request()
            except asyncio.CancelledError:
                self.logger.debug("Cancelled pull task")
            else:
                self.transport.write(request)


class LocalTunnelProtocol(BaseTunnelProtocol):

    def __init__(self, remote_host, url, on_conn_lost=None, ssl_context=None):
        self.cid = None
        self.url = url
        self.remote_host = remote_host
        self.write_queue = asyncio.Queue()
        self.on_conn_lost = on_conn_lost
        self.ssl_context = ssl_context
        self.logger = logging.getLogger('aiotunnel.protocol.LocalTunnelProtocol')
        super().__init__()

    def connection_made(self, transport):
        super().connection_made(transport)
        self.loop.create_task(self.async_open_remote_connection())

    def data_received(self, data):
        self.write_queue.put_nowait(data)

    def eof_received(self):
        self.loop.create_task(self.async_close_remote_connection())
        if self.on_conn_lost:
            self.on_conn_lost.set_result(True)
        super().eof_received()

    async def async_open_remote_connection(self):
        remote = self.remote_host.encode()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, data=remote, ssl_context=self.ssl_context) as resp:
                    cid = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            self.logger.debug("Cannot communicate with %s", self.url)
            await asyncio.sleep(5)
        except:
            self.logger.debug("Connection with server lost")
            await asyncio.sleep(5)
        else:
            self.cid = cid
            scheme = 'HTTPS' if self.ssl_context else 'HTTP'
            self.logger.info("%s over %s to %s", self.remote_host, scheme, self.url)
            self.logger.info("Obtained a client id: %s", cid)
            self.loop.create_task(self.async_write_data())
            self.loop.create_task(self.async_read_data())

    async def async_close_remote_connection(self):
        try:
            async with aiohttp.ClientSession() as session:
                await session.delete(f'{self.url}/{self.cid}', ssl_context=self.ssl_context)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            self.logger.debug("Cannot communicate with %s", self.url)
            await asyncio.sleep(5)
        except:
            self.logger.debug("Connection with server lost")
            await asyncio.sleep(5)

    async def async_write_data(self):
        while not self._shutdown.is_set():
            data = await self.write_queue.get()
            try:
                async with aiohttp.ClientSession() as session:
                    await session.put(f'{self.url}/{self.cid}', data=data, ssl_context=self.ssl_context)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                self.logger.debug("Cannot communicate with %s", self.url)
                await asyncio.sleep(5)
            except:
                self.logger.debug("Connection with server lost")
                self.close()

    async def async_read_data(self):
        while not self._shutdown.is_set():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f'{self.url}/{self.cid}', ssl_context=self.ssl_context) as resp:
                        data = await resp.read()
                        self.transport.write(data)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                self.logger.debug("Cannot communicate with %s", self.url)
                await asyncio.sleep(5)
            except:
                self.logger.debug("Connection with server lost")
                self.close()
