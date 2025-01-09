#!/usr/bin/env python3

"""
demo_ws_client.py

This script demonstrates a simple WebSocket client using the `websockets`
library in Python. The client connects to a WebSocket server running on
localhost at port 9998, sends a greeting message to the server, and prints
the response received from the server.

Usage:
    python3 demo_ws_client.py

Functions:
    - connect(): Asynchronous function that establishes a WebSocket
                 connection, sends a message, and prints the server's
                 response.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import asyncio
import logging
import websockets

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
log = logging.getLogger(__name__)


async def connect():
    """
    Establishes a WebSocket connection to a server, sends a greeting message,
    and handles the response.

    This function attempts to connect to a WebSocket server at the specified
    URI. Upon successful connection, it sends a "Hello, Server!" message to
    the server and waits for a response. The function logs the connection
    status, sent message, and received response. It also handles and logs any
    exceptions that occur during the connection and communication process.

    Exceptions Handled:
        - websockets.exceptions.ConnectionClosedError: Raised when the
          connection is closed unexpectedly.
        - Exception: Catches any other exceptions that may occur during the
          connection or communication.

    Logging:
        - Logs an attempt to connect to the server.
        - Logs a successful connection to the server.
        - Logs the sent message.
        - Logs the received response from the server.
        - Logs any errors that occur during the connection or communication.

    Usage:
        This function should be called within an asyncio event loop.

    Example:
        asyncio.run(connect())
    """

    uri = "ws://localhost:9998"
    log.info("Attempting to connect to %s", uri)
    try:
        async with websockets.connect(uri) as websocket:
            log.info("Connected to the server")
            await websocket.send("Hello, Server!")
            try:
                response = await websocket.recv()
                log.info("Received from server: %s", response)
            except websockets.exceptions.ConnectionClosedError as e:
                log.error("Connection closed while receiving response: %s", e)
            except Exception as e:
                log.error("An error occurred while receiving response: %s", e)
    except websockets.exceptions.ConnectionClosedError as e:
        log.error("Connection closed with error: %s", e)
    except Exception as e:
        log.error("An error occurred: %s", e)

asyncio.run(connect())
