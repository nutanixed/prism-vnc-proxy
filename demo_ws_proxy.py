#!/usr/bin/env python3

"""
demo_ws_proxy.py

This script implements a WebSocket proxy server that forwards messages between
a client and a remote WebSocket server.

The proxy server listens for incoming WebSocket connections and establishes a
connection to a specified remote WebSocket server. Messages received from the
client are forwarded to the remote server, and messages received from the
remote server are forwarded to the client.

Functions:
    proxy_connection(websocket): Handles new connections to the proxy server.
    client_to_server(ws, websocket): Forwards messages from the client to the
        remote server.
    server_to_client(ws, websocket): Forwards messages from the remote server to
        the client.
    main(): Starts the WebSocket proxy server.

Usage:
    Run the script with optional arguments to specify the host, port, and
    remote WebSocket URL.

    Example: python demo_ws_proxy.py --host localhost --port 9998 --remote_url ws://localhost:9999

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

REMOTE_URL = None
ARGS = None


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
    log.info("New connection: %s", url)
    try:
        async with websockets.connect(url) as server_ws:
            log.info("Connected to remote websocket")
            task_client_to_server = asyncio.create_task(client_to_server(server_ws, client_ws))
            task_server_to_client = asyncio.create_task(server_to_client(server_ws, client_ws))

            await task_client_to_server
            await task_server_to_client
            log.info("Connection closed")
    except websockets.exceptions.InvalidURI as e:
        log.error("Invalid URI: %s", e)
    except websockets.exceptions.InvalidHandshake as e:
        log.error("Invalid Handshake: %s", e)
    except websockets.exceptions.ConnectionClosedError as e:
        log.error("Connection closed with error: %s", e)
    except Exception as e:
        log.error("Unexpected error: %s", e)


async def server_to_client(server_ws, client_ws):
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
            log.info("Server to Client: %s", message)
            await client_ws.send(message)
    except websockets.exceptions.ConnectionClosedOK:
        log.info("Connection closed normally in server_to_client")
    except Exception as e:
        log.error("Error in server_to_client: %s", e)


async def client_to_server(server_ws, client_ws):
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
            log.info("Client to Server: %s", message)
            await server_ws.send(message)
    except websockets.exceptions.ConnectionClosedOK:
        log.info("Connection closed normally in client_to_server")
    except Exception as e:
        log.error("Error in client_to_server: %s", e)


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
        proxy_connection, ARGS.host, ARGS.port, logger=log
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
    ARGS = parser.parse_args()

    REMOTE_URL = ARGS.remote_url

    asyncio.run(main())
