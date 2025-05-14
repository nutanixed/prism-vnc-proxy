#!/usr/bin/env python3

"""
wsgi_prism_websocket_proxy.py

WSGI application for proxying WebSocket connections to
Prism Element or Prism Central VNC services.
"""

import asyncio
import logging
import ssl
import uuid as uuid_lib
from typing import Optional, Tuple

import aiohttp
import requests
import urllib3
from aiohttp import web
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s,%(msecs)03dZ [%(levelname)8s] (%(filename)s:%(lineno)s) %(message)s'
)
log = logging.getLogger(__name__)


class WSGIPrismWebsocketProxy:
    """Proxy VNC WebSocket connections via Prism Element or Prism Central."""

    def __init__(self, host: str, user: str, password: str, use_pc: bool = False):
        self._host = host
        self._user = user
        self._password = password
        self._use_prism_central = use_pc

    def _get_session_cookie(self) -> Optional[str]:
        """Authenticate with Prism Element and return the session cookie."""
        log.info("Authenticating with Prism Element at %s as user %s", self._host, self._user)
        session = requests.Session()
        try:
            response = session.post(
                f"https://{self._host}:9440/PrismGateway/j_spring_security_check",
                data={"j_username": self._user, "j_password": self._password},
                verify=False,
                timeout=5
            )
            response.raise_for_status()
            jsess = session.cookies.get("JSESSIONID")
            if not jsess:
                log.error("No JSESSIONID cookie received after authentication")
                return None
            return f"JSESSIONID={jsess}"
        except requests.RequestException as e:
            log.error("Prism Element authentication failed: %s", e)
            return None

    def _get_pc_session_cookie_and_cluster(self, vm_uuid: str) -> Tuple[Optional[str], Optional[str]]:
        """Authenticate with Prism Central and fetch the VM's cluster UUID."""
        log.info("Authenticating with Prism Central at %s as user %s", self._host, self._user)
        session = requests.Session()
        session.verify = False
        try:
            clusters_resp = session.post(
                f"https://{self._host}:9440/api/nutanix/v3/clusters/list",
                auth=(self._user, self._password),
                json={},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            clusters_resp.raise_for_status()
        except requests.RequestException as e:
            log.error("Prism Central authentication failed: %s", e)
            return None, None

        cookies = session.cookies.get_dict()
        cookie_parts = [
            f"{key}={cookies[key]}"
            for key in ['NTNX_IGW_SESSION', 'NTNX_IAM_SESSION', 'NTNX_MERCURY_IAM_SESSION']
            if key in cookies
        ]

        if not cookie_parts:
            log.error("No Prism Central session cookies found")
            return None, None

        cookie_header = "; ".join(cookie_parts)

        try:
            vm_url = f"https://{self._host}:9440/api/nutanix/v3/vms/{vm_uuid}"
            vm_resp = session.get(vm_url, headers={"Content-Type": "application/json"}, timeout=5)
            vm_resp.raise_for_status()
            cluster_uuid = vm_resp.json()["status"]["cluster_reference"]["uuid"]
            return cookie_header, cluster_uuid
        except Exception as e:
            log.error("Failed to fetch VM cluster UUID: %s", e)
            return None, None

    async def prism_websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle incoming WebSocket requests and proxy them to Prism."""
        vm_uuid = request.match_info.get('vm_uuid')
        try:
            uuid_lib.UUID(vm_uuid, version=4)
        except ValueError:
            log.error("Invalid VM UUID: %s", vm_uuid)
            return web.Response(status=400, text="Invalid VM UUID")

        log.info("Received request for VM UUID: %s", vm_uuid)

        client_ws = web.WebSocketResponse(protocols=('binary',))
        await client_ws.prepare(request)
        
        # Track the websocket in the application
        request.app.setdefault('websockets', set()).add(client_ws)
        
        # Make sure we remove the websocket when it's closed
        try:
            if self._use_prism_central:
                cookie, cluster_uuid = self._get_pc_session_cookie_and_cluster(vm_uuid)
            else:
                cookie = self._get_session_cookie()
                cluster_uuid = None

            if not cookie:
                log.error("Authentication failed, closing client WebSocket")
                await client_ws.close()
                return client_ws

            vnc_path = f"/vnc/vm/{vm_uuid}/proxy"
            if cluster_uuid:
                vnc_path += f"?proxyClusterUuid={cluster_uuid}"
            uri = f"wss://{self._host}:9440{vnc_path}"

            log.info("Connecting to backend WebSocket: %s", uri)

            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            headers = {'Cookie': cookie}

            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    server_ws = await session.ws_connect(
                        uri,
                        headers=headers,
                        protocols=('binary',)
                    )
                except Exception as e:
                    log.error("Backend WebSocket connection failed: %s", e)
                    await client_ws.close()
                    return client_ws

                async def _proxy(src: web.WebSocketResponse, dst: web.WebSocketResponse):
                    try:
                        async for msg in src:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await dst.send_str(msg.data)
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                await dst.send_bytes(msg.data)
                            elif msg.type == aiohttp.WSMsgType.CLOSE:
                                await dst.close()
                                break
                    except Exception as e:
                        log.error("Error in proxy: %s", e)
                        if not dst.closed:
                            await dst.close()

                try:
                    await asyncio.gather(
                        _proxy(client_ws, server_ws),
                        _proxy(server_ws, client_ws)
                    )
                except asyncio.CancelledError:
                    log.info("WebSocket proxy task cancelled for VM UUID: %s", vm_uuid)
                    if not server_ws.closed:
                        await server_ws.close()
                    if not client_ws.closed:
                        await client_ws.close()
                except Exception as e:
                    log.error("Error in WebSocket proxy: %s", e)
                    if not server_ws.closed:
                        await server_ws.close()
                    if not client_ws.closed:
                        await client_ws.close()

            log.info("WebSocket proxy closed for VM UUID: %s", vm_uuid)
        finally:
            # Always remove the websocket from tracking when done
            if client_ws in request.app.get('websockets', set()):
                request.app['websockets'].remove(client_ws)
                
        return client_ws
