"""
Unit tests for the WSGIPrismWebsocketProxy class and its associated functions.

This module contains tests for the following functionalities:
    - Handling WebSocket connections with missing UUID.
    - Handling WebSocket connections without a session cookie.
    - Handling WebSocket connections with an invalid URI.
    - Handling WebSocket connections with an invalid handshake.
    - Successful WebSocket connection handling.
    - Client-side WebSocket message handling.
    - Server-side WebSocket message handling.

Fixtures:
    - proxy: Provides an instance of WSGIPrismWebsocketProxy for testing.
    - uuid4: Provides a unique UUID for testing.

Test Cases:
    - test_prism_websocket_handler_missing_uuid: Tests handling of WebSocket
      connections with missing UUID.
    - test_prism_websocket_handler_no_session_cookie: Tests handling of
      WebSocket connections without a session cookie.
    - test_prism_websocket_handler_invalid_uri: Tests handling of WebSocket
      connections with an invalid URI.
    - test_prism_websocket_handler_invalid_handshake: Tests handling of
      WebSocket connections with an invalid handshake.
    - test_prism_websocket_handler_success: Tests successful handling of
      WebSocket connections.
    - test_client_await: Tests client-side WebSocket message handling.
    - test_server_await: Tests server-side WebSocket message handling.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import logging

import uuid

from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import aiohttp
import websockets
import websockets.exceptions

from aiohttp import web
from wsgi_prism_websocket_proxy import WSGIPrismWebsocketProxy, client_await, \
    server_await

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture(name="proxy")
def proxy_setup():
    """
    Creates and returns an instance of WSGIPrismWebsocketProxy with test
    credentials.

    Returns:
        WSGIPrismWebsocketProxy: An instance of WSGIPrismWebsocketProxy
        initialized with 'test_host', 'test_user', and 'test_password'.
    """
    return WSGIPrismWebsocketProxy('test_host', 'test_user', 'test_password')


@pytest.fixture(name="uuid4")
def uuid4_setup():
    """
    Generate a random UUID (Universally Unique Identifier) version 4 and
    return it as a string.

    Returns:
        str: A randomly generated UUID version 4.
    """
    return str(uuid.uuid4())


@pytest.mark.asyncio
async def test_prism_websocket_handler_missing_uuid(proxy):
    """
    Test the `prism_websocket_handler` method of the proxy when the UUID is
    missing.

    This test verifies that the `prism_websocket_handler` method returns a 400
    status code and an appropriate error message when the UUID is not provided
    in the request.

    Args:
        proxy: The instance of the proxy being tested.

    Assertions:
        - The response status code should be 400.
        - The response text should indicate that the VM UUID is required.
    """
    logger.debug("Starting test_prism_websocket_handler_missing_uuid")
    request = MagicMock()
    request.match_info.get.return_value = None
    response = await proxy.prism_websocket_handler(request)
    assert response.status == 400
    assert response.text == "VM UUID is required"
    logger.debug("Completed test_prism_websocket_handler_missing_uuid")


@pytest.mark.asyncio
async def test_prism_websocket_handler_no_session_cookie(proxy, uuid4):
    """
    Test the `prism_websocket_handler` method of the `proxy` object when
    there is no session cookie.

    This test ensures that the `prism_websocket_handler` method raises an
    `HTTPBadRequest` exception when the session cookie is not present in the
    request.

    Args:
        proxy: The proxy object being tested.
        uuid4: A UUID value used to simulate the request's match information.

    Steps:
    1. Create a mock request object.
    2. Set the return value of the request's match_info.get method to the
       provided UUID.
    3. Patch the `_get_session_cookie` method of the proxy object to return
       None.
    4. Assert that calling `prism_websocket_handler` with the mock request
       raises an `HTTPBadRequest` exception.
    """
    logger.debug("Starting test_prism_websocket_handler_no_session_cookie")
    request = MagicMock()
    request.match_info.get.return_value = uuid4
    with patch.object(proxy, '_get_session_cookie', return_value=None):
        with pytest.raises(web.HTTPBadRequest):
            await proxy.prism_websocket_handler(request)
    logger.debug("Completed test_prism_websocket_handler_no_session_cookie")


@pytest.mark.asyncio
async def test_prism_websocket_handler_invalid_uri(proxy, uuid4):
    """
    Test the `prism_websocket_handler` method of the proxy with an invalid URI.

    This test ensures that the `prism_websocket_handler` method correctly
    handles the case where an invalid URI is provided. It mocks the necessary
    components and verifies that an HTTPBadRequest exception is raised.

    Args:
        proxy: The proxy instance being tested.
        uuid4: A mock UUID value used for the request.

    Raises:
        web.HTTPBadRequest: If the URI is invalid.
    """
    logger.debug("Starting test_prism_websocket_handler_invalid_uri")
    request = MagicMock()
    request.match_info.get.return_value = uuid4
    with patch.object(proxy, '_get_session_cookie', return_value='test_cookie'):
        with patch('websockets.connect',
                   side_effect=websockets.exceptions.InvalidURI('test_uri',
                                                                'Invalid URI')):
            with pytest.raises(web.HTTPBadRequest):
                await proxy.prism_websocket_handler(request)
    logger.debug("Completed test_prism_websocket_handler_invalid_uri")


@pytest.mark.asyncio
async def test_prism_websocket_handler_invalid_handshake(proxy, uuid4):
    """
    Test the `prism_websocket_handler` method of the `proxy` object when an
    invalid handshake occurs during a WebSocket connection.

    This test simulates an invalid handshake exception raised by the
    `websockets.connect` method and verifies that the
    `prism_websocket_handler` method raises an HTTPBadRequest exception in
    response.

    Args:
        proxy: The proxy object whose `prism_websocket_handler` method is
        being tested.
        uuid4: A mock UUID value used to simulate the request's match_info.

    Setup:
        - Mocks the request object and sets its `match_info.get` method to
          return the mock UUID.
        - Patches the `_get_session_cookie` method of the proxy object to
          return a test cookie.
        - Patches the `websockets.connect` method to raise an
          `InvalidHandshake` exception.

    Assertions:
        - Verifies that the `prism_websocket_handler` method raises an
          `HTTPBadRequest` exception when an invalid handshake occurs.
    """
    logger.debug("Starting test_prism_websocket_handler_invalid_handshake")
    request = MagicMock()
    request.match_info.get.return_value = uuid4
    with patch.object(proxy, '_get_session_cookie', return_value='test_cookie'):
        with patch('websockets.connect',
                   side_effect=websockets.exceptions.InvalidHandshake):
            with pytest.raises(web.HTTPBadRequest):
                await proxy.prism_websocket_handler(request)
    logger.debug("Completed test_prism_websocket_handler_invalid_handshake")


@pytest.mark.asyncio
async def test_prism_websocket_handler_success(proxy, uuid4):
    """
    Test the `prism_websocket_handler` method of the proxy for a successful
    connection.

    This test verifies that the `prism_websocket_handler` correctly handles a
    websocket connection when provided with a valid UUID and session cookie.

    Args:
        proxy: The instance of the proxy being tested.
        uuid4: A mock UUID to simulate the request's match_info.

    Steps:
    1. Mock the request object and set its `match_info.get` method to return
       the provided UUID.
    2. Patch the `_get_session_cookie` method of the proxy to return a test
       cookie.
    3. Patch the `websockets.connect` method to return an asynchronous mock.
    4. Patch the `asyncio.create_task` method to return an asynchronous mock.
    5. Call the `prism_websocket_handler` method with the mocked request.
    6. Assert that the response status is 101, indicating a successful
       websocket connection.
    """
    logger.debug("Starting test_prism_websocket_handler_success")
    request = MagicMock()
    request.match_info.get.return_value = uuid4
    with patch.object(proxy, '_get_session_cookie', return_value='test_cookie'):
        with patch('websockets.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = AsyncMock()
            with patch('asyncio.create_task', new_callable=AsyncMock):
                response = await proxy.prism_websocket_handler(request)
                assert response.status == 101
    logger.debug("Completed test_prism_websocket_handler_success")


@pytest.mark.asyncio
async def test_client_await():
    """
    Test the `client_await` function.

    This test simulates a WebSocket client and server interaction where the
    client receives a 'close' message. It verifies that the `client_await`
    function properly handles the message and closes the client WebSocket
    connection.

    Steps:
    1. Create mock objects for the request, client WebSocket, and server
       WebSocket.
    2. Set up the client WebSocket to simulate receiving a 'close' message.
    3. Call the `client_await` function with the mock objects.
    4. Verify that the client WebSocket's `close` method is called once.

    Assertions:
    - The client WebSocket's `close` method is called exactly once.
    """
    logger.debug("Starting test_client_await")
    request = MagicMock()
    client_ws = AsyncMock()
    server_ws = AsyncMock()
    client_ws.__aiter__.return_value = [
        MagicMock(type=aiohttp.WSMsgType.TEXT, data='close')]
    await client_await(request, client_ws, server_ws)
    client_ws.close.assert_called_once()
    logger.debug("Completed test_client_await")


@pytest.mark.asyncio
async def test_server_await():
    """
    Test the server_await function.

    This test function mocks the request, server WebSocket, and client
    WebSocket objects, and verifies that the server_await function correctly
    processes a message from the server WebSocket and sends it to the client
    WebSocket.

    Steps:
    1. Mock the request, server WebSocket, and client WebSocket objects.
    2. Set the server WebSocket to return a test message when iterated.
    3. Call the server_await function with the mocked objects.
    4. Assert that the client WebSocket's send_str method was called once with
       the test message.

    Assertions:
    - The client WebSocket's send_str method is called once with the message
      'test_message'.
    """
    logger.debug("Starting test_server_await")
    request = MagicMock()
    server_ws = AsyncMock()
    client_ws = AsyncMock()
    server_ws.__aiter__.return_value = ['test_message']
    await server_await(request, server_ws, client_ws)
    client_ws.send_str.assert_called_once_with('test_message')
    logger.debug("Completed test_server_await")
