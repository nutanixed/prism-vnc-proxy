#!/usr/bin/env python3

"""
demo-ws-server.py

This script sets up a simple WebSocket server using the aiohttp library. The server listens on all network interfaces
at port 9999 and accepts WebSocket connections. Upon accepting a connection, it sends the remote address of the client
back to the client and then closes the connection.

Modules:
    asyncio: Provides support for asynchronous programming.
    aiohttp.web: Provides the web server and WebSocket support.

Functions:
    websocket_handler(request: web.Request) -> web.StreamResponse:
        Handles incoming WebSocket connections, sends the client's remote address, and closes the connection.
    
    main():
        Sets up and starts the WebSocket server, and keeps it running indefinitely.

Usage:
    Run this script directly to start the WebSocket server.
    
Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import asyncio

from aiohttp import web, WSMsgType, WSMessage

HOST = '0.0.0.0'
PORT = 9999

app = web.Application()


async def websocket_handler(request: web.Request) -> web.StreamResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await ws.send_str(str(request.remote))
    await ws.close()
    print('accepted connection from', request.remote)
    return ws


app.add_routes([
    web.get('/', websocket_handler)
])


async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=HOST, port=PORT)
    await site.start()
    print('server is running')
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())