#!/usr/bin/env python3

"""
demo-ws-proxy.py

This script implements a WebSocket proxy server that forwards messages between
a client and a remote WebSocket server.

The proxy server listens for incoming WebSocket connections and establishes a
connection to a specified remote WebSocket server. Messages received from the
client are forwarded to the remote server, and messages received from the
remote server are forwarded to the client.

Functions:
    proxy_connection(websocket): Handles new connections to the proxy server.
    clientToServer(ws, websocket): Forwards messages from the client to the
        remote server.
    serverToClient(ws, websocket): Forwards messages from the remote server to
        the client.
    main(): Starts the WebSocket proxy server.

Usage:
    Run the script with optional arguments to specify the host, port, and
    remote WebSocket URL.

    Example: python demo-ws-proxy.py --host localhost --port 9998 --remote_url ws://localhost:9999

Arguments:
    --host: Host to bind to (default: 'localhost').
    --port: Port to bind to (default: 9998).
    --remote_url: Remote WebSocket URL (default: 'ws://localhost:9999').

Logging:
    The script logs various events and errors, including new connections,
    message forwarding, and connection closures.

Author:
    Jon Kohler (jon@nutanix.com)
    Originally based on Gist:
        https://gist.github.com/bsergean/bad452fa543ec7df6b7fd496696b2cd8

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import argparse
import asyncio
import logging
import websockets

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
log = logging.getLogger(__name__)


async def proxy_connection(client_ws):
    """
    Handles a new client connection to a remote websocket server.

    This function establishes a connection to a remote websocket server
    specified by the REMOTE_URL. It creates two asynchronous tasks to handle
    bidirectional communication between the client and the server. The
    function logs the connection status and handles various exceptions that
    may occur during the connection process.

    Args:
        client_ws (websockets.WebSocketClientProtocol): The websocket
            connection from the client.

    Raises:
        websockets.exceptions.InvalidURI: If the URI of the remote websocket
            server is invalid.
        websockets.exceptions.InvalidHandshake: If the handshake with the
            remote websocket server fails.
        websockets.exceptions.ConnectionClosedError: If the connection to the
            remote websocket server is closed with an error.
        Exception: For any other unexpected errors.

    Logs:
        Logs the status of the connection, including successful connections,
        connection closures, and any errors encountered.
    """

    url = REMOTE_URL
    log.info(f"New connection: {url}")
    try:
        async with websockets.connect(url) as server_ws:
            log.info("Connected to remote websocket")
            taskA = asyncio.create_task(clientToServer(server_ws, client_ws))
            taskB = asyncio.create_task(serverToClient(server_ws, client_ws))

            await taskA
            await taskB
            log.info("Connection closed")
    except websockets.exceptions.InvalidURI as e:
        log.error(f"Invalid URI: {e}")
    except websockets.exceptions.InvalidHandshake as e:
        log.error(f"Invalid Handshake: {e}")
    except websockets.exceptions.ConnectionClosedError as e:
        log.error(f"Connection closed with error: {e}")
    except Exception as e:
        log.error(f"Unexpected error: {e}")


async def serverToClient(server_ws, client_ws):
    """
    Handles the communication from the server WebSocket to the client
    WebSocket.

    This function listens for messages from the server WebSocket and
    forwards them to the client WebSocket. It logs each message that is
    forwarded. If the connection is closed normally, it logs this event.
    Any other exceptions are caught and logged as errors.

    Args:
        server_ws (websockets.WebSocketClientProtocol): The WebSocket
            connection from the server.
        client_ws (websockets.WebSocketClientProtocol): The WebSocket
            connection to the client.

    Raises:
        websockets.exceptions.ConnectionClosedOK: If the connection is
            closed normally.
        Exception: For any other exceptions that occur during message
            forwarding.
    """

    try:
        async for message in server_ws:
            log.info(f"Server to Client: {message}")
            await client_ws.send(message)
    except websockets.exceptions.ConnectionClosedOK:
        log.info("Connection closed normally in serverToClient")
    except Exception as e:
        log.error(f"Error in serverToClient: {e}")


async def clientToServer(server_ws, client_ws):
    """
    Handles the communication from the client WebSocket to the server
    WebSocket.

    This function listens for messages from the client WebSocket and
    forwards them to the server WebSocket. It logs each message sent from
    the client to the server. If the connection is closed normally, it logs
    this event. Any other exceptions encountered during the process are also
    logged.

    Args:
        server_ws (websockets.WebSocketServerProtocol): The WebSocket
            connection to the server.
        client_ws (websockets.WebSocketClientProtocol): The WebSocket
            connection from the client.

    Raises:
        websockets.exceptions.ConnectionClosedOK: If the connection is closed
            normally.
        Exception: For any other exceptions that occur during message
            forwarding.
    """

    try:
        async for message in client_ws:
            log.info(f"Client to Server: {message}")
            await server_ws.send(message)
    except websockets.exceptions.ConnectionClosedOK:
        log.info("Connection closed normally in clientToServer")
    except Exception as e:
        log.error(f"Error in clientToServer: {e}")


async def main():
    """
    Main entry point for the WebSocket proxy server.

    This function sets up and starts the WebSocket server using the
    `websockets.serve` function, which listens for incoming connections
    on the specified host and port. The server will handle connections
    using the `proxy_connection` function and log activities using the
    provided logger.

    The server will run indefinitely until it is closed.

    Args:
        None

    Returns:
        None
    """

    start_server = await websockets.serve(
        proxy_connection, args.host, args.port, logger=log
    )
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
