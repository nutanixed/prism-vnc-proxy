#!/usr/bin/env python3

"""
demo-ws-proxy.py

This script implements a WebSocket proxy server that forwards messages between a client and a remote WebSocket server.

The proxy server listens for incoming WebSocket connections and establishes a connection to a specified remote WebSocket server.
Messages received from the client are forwarded to the remote server, and messages received from the remote server are forwarded to the client.

Functions:
    hello(websocket): Handles new connections to the proxy server.
    clientToServer(ws, websocket): Forwards messages from the client to the remote server.
    serverToClient(ws, websocket): Forwards messages from the remote server to the client.
    main(): Starts the WebSocket proxy server.

Usage:
    Run the script with optional arguments to specify the host, port, and remote WebSocket URL.
    Example: python demo-ws-proxy.py --host localhost --port 9998 --remote_url ws://localhost:9999

Arguments:
    --host: Host to bind to (default: 'localhost').
    --port: Port to bind to (default: 9998).
    --remote_url: Remote WebSocket URL (default: 'ws://localhost:9999').

Logging:
    The script logs various events and errors, including new connections, message forwarding, and connection closures.
    
Author:
    Jon Kohler (jon@nutanix.com)
    Based on Gist: https://gist.github.com/bsergean/bad452fa543ec7df6b7fd496696b2cd8

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import argparse
import asyncio
import logging
import websockets
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
log = logging.getLogger(__name__)

async def hello(websocket):
    '''Called whenever a new connection is made to the server'''

    url = REMOTE_URL
    log.info(f"New connection: {url}")
    async with websockets.connect(url) as ws:
        log.info("Connected to remote websocket")
        taskA = asyncio.create_task(clientToServer(ws, websocket))
        taskB = asyncio.create_task(serverToClient(ws, websocket))

        await taskA
        await taskB
        log.info("Connection closed")

async def clientToServer(ws, websocket):
    try:
        async for message in ws:
            log.info(f"Client to Server: {message}")
            await websocket.send(message)
    except websockets.exceptions.ConnectionClosedOK:
        log.info("Connection closed normally in clientToServer")
    except Exception as e:
        log.error(f"Error in clientToServer: {e}")


async def serverToClient(ws, websocket):
    try:
        async for message in websocket:
            log.info(f"Server to Client: {message}")
            await ws.send(message)
    except websockets.exceptions.ConnectionClosedOK:
        log.info("Connection closed normally in serverToClient")
    except Exception as e:
        log.error(f"Error in serverToClient: {e}")

async def main():
    start_server = await websockets.serve(hello, args.host, args.port, logger=log)
    await start_server.wait_closed()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='websocket proxy.')
    parser.add_argument('--host', help='Host to bind to.',
                        default='localhost')
    parser.add_argument('--port', help='Port to bind to.',
                        default=9998)
    parser.add_argument('--remote_url', help='Remote websocket url',
                        default='ws://localhost:9999')
    args = parser.parse_args()

    REMOTE_URL = args.remote_url

    asyncio.run(main())
