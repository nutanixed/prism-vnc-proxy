"""
This module contains unit tests for the WebSocket server implemented in the
`demo_ws_server` module.

Classes:
    TestWebSocketServer: A test case class for testing the WebSocket server.

Functions:
    get_application: Sets up the web application with the WebSocket handler
        route.
    test_websocket_handler: Tests the WebSocket connection and message
        reception.
    test_websocket_handler_close: Tests the WebSocket connection closure.

Logging:
    Configures logging to output informational messages during the tests.

Usage:
    Run this module directly to execute the tests.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import logging

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from demo_ws_server import websocket_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWebSocketServer(AioHTTPTestCase):
    """
    Test suite for WebSocket server using AioHTTPTestCase.

    This class contains tests to verify the functionality of a WebSocket
    server implemented using the aiohttp library. It includes tests for
    establishing a WebSocket connection, receiving messages, and closing
    the connection.

    Methods:
        get_application: Sets up the aiohttp web application with the
            WebSocket route.
        test_websocket_handler: Tests the WebSocket handler for receiving
            a message.
        test_websocket_handler_close: Tests the WebSocket handler for
            closing the connection.
    """

    async def get_application(self):
        app = web.Application()
        app.add_routes([web.get('/', websocket_handler)])
        return app

    async def test_websocket_handler(self):
        """
        Test the websocket handler by connecting to the websocket server and
        verifying the received message.

        This coroutine performs the following steps:
        1. Logs the start of the test.
        2. Connects to the websocket server at the root path ('/').
        3. Waits to receive a message from the websocket server.
        4. Logs the received message.
        5. Asserts that the message type is text.
        6. Asserts that the message data contains the string "connected,
           hello!".
        7. Logs the completion of the test.

        Raises:
            AssertionError: If the received message type is not text or if the
                    message data does not contain the expected string.
        """
        logger.info("Starting test_websocket_handler")
        async with self.client.ws_connect('/') as ws:
            msg = await ws.receive()
            logger.info("Received message: %s", msg.data)
            assert msg.type == web.WSMsgType.TEXT
            assert "connected, hello!" in msg.data
        logger.info("Finished test_websocket_handler")

    async def test_websocket_handler_close(self):
        """
        Test the WebSocket handler close functionality.

        This test connects to the WebSocket server, closes the connection,
        and verifies that the WebSocket is closed.

        Steps:
        1. Connect to the WebSocket server at the root path.
        2. Close the WebSocket connection.
        3. Log that the WebSocket has been closed.
        4. Assert that the WebSocket is indeed closed.
        5. Log the completion of the test.

        This test ensures that the WebSocket handler correctly handles
        the closing of a WebSocket connection.
        """
        logger.info("Starting test_websocket_handler_close")
        async with self.client.ws_connect('/') as ws:
            await ws.close()
            logger.info("WebSocket closed")
            assert ws.closed
        logger.info("Finished test_websocket_handler_close")
