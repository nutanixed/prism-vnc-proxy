#!/usr/bin/env python3

"""
wsgi_prism_websocket_proxy.py

This module provides a WSGI application for proxying WebSocket connections to
a Prism server.

Classes:
    WSGIPrismWebsocketProxy: A class that handles WebSocket proxying to a Prism
    server.

WSGIPrismWebsocketProxy:
    Methods:
        __init__(self, host, user, password):
            Initializes the proxy with the given host, user, and password.
        _get_session_cookie(self):
        async prism_websocket_handler(self, request):
            Handles incoming WebSocket requests, establishes a connection to
            the Prism server, and proxies messages between the client and the
            server.
            Parameters:
                request (aiohttp.web.Request): The incoming WebSocket request.
                aiohttp.web.WebSocketResponse: The WebSocket response to the
                client.

Functions:
    async clientAwait(request, client_ws, server_ws):
        This coroutine listens for messages from the client WebSocket (e.g.,
        noVNC/Browser) and processes them accordingly. Depending on the type
        of message received, it performs different actions such as sending
        messages to the server WebSocket, responding to ping/pong frames, or
        closing the connection.
            client_ws (aiohttp.web.WebSocketResponse): The WebSocket connection
                to the client.
            server_ws (aiohttp.ClientWebSocketResponse): The WebSocket
                connection to the server.
            aiohttp.web.WebSocketResponse: The client WebSocket connection
                after processing.
    async serverAwait(request, server_ws, client_ws):
        This coroutine listens for messages from the server WebSocket (e.g.,
        Prism) and forwards them to the client WebSocket (e.g., noVNC/Browser).
        It prepares the client WebSocket connection and processes messages
        until the server WebSocket connection is closed.

Logging:
  Logs information and errors to the console using the logging module.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

from aiohttp import web

import aiohttp
import asyncio
import logging
import requests
import ssl
import websockets

# Suppress only the single InsecureRequestWarning from urllib3 needed for
# this script
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(funcName)s]: %(message)s')
log = logging.getLogger(__name__)


class WSGIPrismWebsocketProxy(object):
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def _get_session_cookie(self):
        """
        Authenticates with the Prism server and retrieves the session cookie.

        This method sends a POST request to the Prism server's authentication
        endpoint using the provided username and password. If the
        authentication is successful and a session cookie is received, the
        method returns the session cookie in the format "JSESSIONID=<cookie_value>".
        If authentication fails or no session cookie is received, the method
        logs the appropriate error and returns None.

        Returns:
            str: The session cookie in the format "JSESSIONID=<cookie_value>"
            if authentication is successful and a session cookie is received.
            Otherwise, returns None.

        Raises:
            requests.exceptions.HTTPError: If an HTTP error occurs during the
            authentication request.
            requests.exceptions.RequestException: If a request exception occurs
            during the authentication request.
        """

        log.info(
            f"Authenticating with Prism at {self._host} as user {self._user}")
        session = requests.Session()
        try:
            response = session.post(
                "https://%s:9440/PrismGateway/j_spring_security_check" % self._host,
                data={
                    "j_username": self._user,
                    "j_password": self._password,
                },
                verify=False,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                log.error("Prism Unauthorized: Invalid username or password")
            else:
                log.error("Prism HTTP error occurred: %s" % (e,))
            return None
        except requests.exceptions.RequestException as e:
            log.error("Failed to connect to Prism: %s" % (e,))
            return None

        if "JSESSIONID" not in session.cookies:
            log.debug(f"Response headers: {response.headers}")
            log.debug(f"Session Cookies received: {session.cookies}")
            log.error("Authentication with Prism successful, but no JSESSIONID")
            return None

        return "JSESSIONID=" + session.cookies["JSESSIONID"]

    async def prism_websocket_handler(self, request):
        """
        Handles incoming WebSocket requests and proxies them to a VNC server.

        Args:
            request (aiohttp.web.Request): The incoming HTTP request.

        Returns:
            aiohttp.web.WebSocketResponse: The WebSocket response to be sent
            back to the client.

        The function performs the following steps:
        1. Extracts the VM UUID from the request.
        2. Constructs the VNC WebSocket URL using the extracted UUID.
        3. Attempts to establish a WebSocket connection to the VNC server.
        4. Handles various exceptions that may occur during the connection
           process.
        5. If the connection is successful, creates tasks to forward messages
           between the client and server WebSocket connections.
        6. Waits for the tasks to complete and then closes the connection.

        Raises:
            aiohttp.web.HTTPBadRequest: If the VM UUID is missing in the
                request.
            websockets.exceptions.InvalidURI: If the constructed WebSocket URI
                is invalid.
            websockets.exceptions.InvalidHandshake: If the WebSocket handshake
                fails.
            websockets.exceptions.InvalidStatus: If the WebSocket connection is
                rejected with an invalid status.
            Exception: For any other unexpected errors.
        """
        uuid = request.match_info.get('vm_uuid', None)
        if uuid is None:
            log.error("VM UUID is missing in the request")
            return web.Response(status=400, text="VM UUID is required")

        log.info(f"Received request for VM: {uuid}")
        vnc_rel_url = str(request.rel_url).replace("/proxy", "/vnc/vm", 1)
        vnc_rel_url += "/proxy"
        uri = "wss://%s:9440%s" % (self._host, vnc_rel_url)

        client_ws = web.WebSocketResponse(protocols="binary")
        cookie = self._get_session_cookie()
        if cookie is None:
            log.error("Failed to obtain session cookie. Closing connection.")
            await client_ws.prepare(request)
            await client_ws.close()
            return client_ws
        log.info(f"New connection: {uri}")
        headers = {
            "Cookie": "%s" % cookie
        }

        try:
            try:
                server_ws = await websockets.connect(
                    uri,
                    additional_headers=headers,
                    ssl=ssl._create_unverified_context())
            except websockets.exceptions.InvalidHandshake as e:
                log.warning(
                    f"Invalid Handshake on first attempt: {e}. Retrying...")
                await asyncio.sleep(1)  # Wait a bit before retrying
                server_ws = await websockets.connect(
                    uri,
                    additional_headers=headers,
                    ssl=ssl._create_unverified_context())
        except websockets.exceptions.InvalidURI as e:
            log.error(f"Invalid URI: {e}")
            await client_ws.prepare(request)
            await client_ws.close()
            return client_ws
        except websockets.exceptions.InvalidHandshake as e:
            log.error(f"Invalid Handshake: {e}")
            await client_ws.prepare(request)
            await client_ws.close()
            return client_ws
        except websockets.exceptions.InvalidStatus as e:
            if e.status_code == 401:
                log.error(
                    "Server rejected WebSocket connection: HTTP 401 Unauthorized")
            else:
                log.error(f"Invalid Status: {e}")

            await client_ws.prepare(request)
            await client_ws.close()
            return client_ws
        except Exception as e:
            log.error(f"Unexpected error: {e}")
            await client_ws.prepare(request)
            await client_ws.close()
            return client_ws

        # At this point, we have the following:
        #   - A valid websocket request (request)
        #   - A connection open from the browswer (client_ws)
        #   - A connection open to prism (server_ws)
        # Now this is time to glue them together to pass messages.
        # We will create two tasks:
        taskA = asyncio.create_task(clientAwait(request, client_ws, server_ws))
        taskB = asyncio.create_task(serverAwait(request, server_ws, client_ws))

        await taskA
        await taskB
        log.info("Connection closed")

        return client_ws


async def clientAwait(request, client_ws, server_ws):
    """
    Handles the client side of the WebSocket proxy.
    This coroutine listens for messages from the client WebSocket (e.g.,
    noVNC/Browser) and processes them accordingly. Depending on the type of
    message received, it performs different actions such as sending messages
    to the server WebSocket, responding to ping/pong frames, or closing the
    connection.

    Args:
        request (aiohttp.web.Request): The incoming HTTP request.
        client_ws (aiohttp.web.WebSocketResponse): The WebSocket connection to
            the client.
        server_ws (aiohttp.ClientWebSocketResponse): The WebSocket connection
            to the server.

    Returns:
        aiohttp.web.WebSocketResponse: The client WebSocket connection after
            processing.

    Raises:
        Exception: If there is an error sending a message to the server.
    """
    log.debug("CLIENT SIDE PROCESSING")
    await client_ws.prepare(request)

    # Here we are listening for any messages from the client side of
    # the proxy (e.g. noVNC/Browser)
    async for msg in client_ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                log.debug("Received TEXT with close message")
                await client_ws.close()
            else:
                log.debug("Received TEXT message")
                await server_ws.send(msg.data + '/answer')
        elif msg.type == aiohttp.WSMsgType.BINARY:
            log.debug("Received BINARY message")
            try:
                await server_ws.send(msg.data)
            except Exception as e:
                log.error(
                    f"Error sending message to server: {e} with message: {msg.data}")
                break
        elif msg.type == aiohttp.WSMsgType.PING:
            log.debug("Received PING message")
            await server_ws.ping()
        elif msg.type == aiohttp.WSMsgType.PONG:
            log.debug("Received PONG message")
            await server_ws.pong()
        elif msg.type == aiohttp.WSMsgType.CLOSE:
            log.debug("Received CLOSE message")
            await client_ws.close()
        elif msg.type == aiohttp.WSMsgType.ERROR:
            log.error('ws connection closed with exception %s' %
                      client_ws.exception())

    log.debug('CLIENT SIDE websocket connection closed')

    return client_ws


async def serverAwait(request, server_ws, client_ws):
    """
    Handles the server side of the WebSocket proxy.
    This coroutine listens for messages from the server WebSocket (e.g., Prism)
    and forwards them to the client WebSocket (e.g., noVNC/Browser). It
    prepares the client WebSocket connection and processes messages until the
    server WebSocket connection is closed.

    Args:
        request: The HTTP request object associated with the WebSocket connection.
        server_ws: The WebSocket connection to the server side (e.g., prism).
        client_ws: The WebSocket connection to the client side (e.g., noVNC/Browser).

    Returns:
        None

    Raises:
        Exception: If there is an error sending a message to the client WebSocket.
    """
    log.debug("SERVER SIDE PROCESSING")
    await client_ws.prepare(request)

    # Here we are listening for any messages from the server side of
    # the proxy (e.g. prism) and then send them along to the client
    # (noVNC/Browser)
    async for message in server_ws:
        log.debug(f"Forward to Client: {message}")
        if isinstance(message, str):
            try:
                await client_ws.send_str(message)
            except Exception as e:
                log.error(
                    f"Error sending message to client: {e} with message: {message}")
                break
        else:
            try:
                await client_ws.send_bytes(message)
            except Exception as e:
                log.error(
                    f"Error sending message to client: {e} with message: {message}")
                break

    log.debug('SERVER SIDE websocket connection closed')
