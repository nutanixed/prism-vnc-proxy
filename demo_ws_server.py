#!/usr/bin/env python3

"""
demo_ws_server.py

This script sets up a simple WebSocket server using the aiohttp library.
The server listens on all network interfaces at port 9999 and accepts
WebSocket connections. Upon accepting a connection, it sends the remote
address of the client back to the client and then closes the connection.

Modules:
    asyncio: Provides support for asynchronous programming.
    aiohttp.web: Provides the web server and WebSocket support.

Functions:
    websocket_handler(request: web.Request) -> web.StreamResponse:
        Handles incoming WebSocket connections, sends the client's remote
        address, and closes the connection.

    main():
        Sets up and starts the WebSocket server, and keeps it running
        indefinitely.

Usage:
    Run this script directly to start the WebSocket server.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import asyncio
import logging

from aiohttp import web

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
log = logging.getLogger(__name__)

HOST = '0.0.0.0'
PORT = 9999


async def websocket_handler(request: web.Request) -> web.StreamResponse:
    """
    Handle incoming WebSocket connections.

    This asynchronous function handles WebSocket connections by preparing
    the WebSocket response, sending the remote address of the request as a
    string, logging the accepted connection, and handling any exceptions
    that occur during the process. Finally, it ensures that the WebSocket
    is closed before returning the response.

    Args:
        request (web.Request): The incoming HTTP request.

    Returns:
        web.StreamResponse: The WebSocket response.

    Raises:
        Exception: For any other errors that occur during the handling of
        the WebSocket connection.
    """

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    try:
        await ws.send_str(str(request.remote + " connected, hello!"))
        log.info('accepted connection from %s', request.remote)
    except Exception as e:
        log.error('error handling connection from %s: %s',
                  request.remote, str(e))
    finally:
        await ws.close()
    return ws


async def main(app_context):
    """
    Asynchronous main function to set up and start the web server.

    This function initializes the web application runner, sets up the runner,
    creates a TCP site with the specified host and port, and starts the site.
    It then prints a message indicating that the server is running and waits
    indefinitely for an event to occur.

    Returns:
        None

    Raises:
        asyncio.CancelledError: If the server shutdown is initiated by the user.
        Exception: If there is an error starting the server.
    """

    try:
        runner = web.AppRunner(app_context)
        await runner.setup()
        site = web.TCPSite(runner, host=HOST, port=PORT)
        await site.start()
        log.info('server is running')
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            log.info('server shutdown initiated by user')
    except (OSError, web.HTTPException) as e:
        log.error('error starting server: %s', str(e))
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.get('/', websocket_handler)])
    asyncio.run(main(app))
