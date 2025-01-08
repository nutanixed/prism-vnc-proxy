#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: gasmith@nutanix.com
#

import gevent
import logging
import requests
import ssl
import thread
import threading
import websocket

from wsgi_web_socket import WebSocketWSGI

log = logging.getLogger(__name__)

class WSGIPrismWebsocketProxy(object):
  def __init__(self, wsgi_handler, host, user, password):
    self._wsgi_handler = wsgi_handler
    self._host = host
    self._user = user
    self._password = password

  def _get_session_cookie(self):
    """
    Logs into Prism and obtains a session cookie.

    Returns:
      str: A cookie string (e.g., "JSESSIONID=..."), or None on failure.
    """
    log.info("Authenticating with Prism at %s" % (self._host,))
    s = requests.Session()
    resp = s.post(
        "https://%s:9440/PrismGateway/j_spring_security_check" % (self._host,),
        params={
          "j_username": self._user,
          "j_password": self._password,
        },
        verify=False,
    )
    code, text = resp.status_code, resp.text.strip()
    if (code, text) != (200, "Success"):
      log.error("Failed to connect to Prism: %d %s" % (code, text))
      return None

    if "JSESSIONID" not in s.cookies:
      log.error("Authentication with Prism successful, but no JSESSIONID")
      return None

    return "JSESSIONID=" + s.cookies["JSESSIONID"]

  def _open_websock(self, environ, session_cookie, server_url):
    """
    Opens a websocket via Prism using the provided session cookie.

    Args:
      environ (dict): WSGI environment.
      session_cookie (str): A cookie string (e.g., "JSESSIONID=...").
      server_url (str): Relative server websocket URL.
    Returns:
      WebSocket: The open websocket.
    Raises:
      WebSocketException: Failed to open websocket.
    """
    proxy_headers = (
        "HTTP_CONNECTION",
        "HTTP_SEC_WEBSOCKET_VERSION",
        "HTTP_SEC_WEBSOCKET_KEY",
        "HTTP_UPGRADE",
    )
    url = "wss://%s:9440%s" % (self._host, server_url)
    log.info("Opening websocket %s" % (url,))
    return websocket.create_connection(
        url,
        cookie=session_cookie,
        headers=dict(
          (name[5:], environ[name])
            for name in proxy_headers
              if name in environ
        ),
        sslopt={
          "cert_reqs": ssl.CERT_NONE,
        })

  def _proxy_traffic(self, client, server):
    """
    Proxies websocket frames between the client and server.
    """
    done = threading.Event()

    def serve(ws_pair):
      names = [ "%s:%d" % ws.sock.getsockname() for ws in ws_pair ]
      while True:
        try:
          frame = ws_pair[0].recv_frame()
        except Exception as ex:
          log.error("Failed to receive from %s: %s" % (names[0], ex))
          break
        if not frame:
          log.error("Invalid frame from %s" % (names[0],))
          break
        try:
          ws_pair[1].send_frame(frame)
        except Exception as ex:
          log.error("Failed to send to %s: %s" % (names[1], ex))
          break
        if frame.opcode == frame.OPCODE_CLOSE:
          log.info("Connection closed by %s" % (names[0],))
          break
      done.set()

    threads = []
    threads.append(gevent.spawn(serve, (client, server)))
    threads.append(gevent.spawn(serve, (server, client)))

    done.wait()
    map(lambda thread: thread.kill(), threads)

    client.close()
    server.close()

  def _handle(self, environ, start_response, server_url):
    """
    Handles an incoming HTTP request.

    Upgrades the connection to a websocket and starts the proxy.

    Args:
      environ (dict): WSGI environment.
      start_response (callable): WSGI response callback.
      server_url (str): Relative server websocket URL to proxy.
    Returns:
      A list of strings on failure, or a magic response on success.
    """
    cookie = self._get_session_cookie()
    if cookie is None:
      start_response("401 Unauthorized", [])
      return [ "Failed to obtain authenticated session from Prism" ]

    @WebSocketWSGI
    def do_proxy(client):
      server = self._open_websock(environ, cookie, server_url)
      self._proxy_traffic(client, server)

    return do_proxy(environ, start_response)

  def add_handler(self, url, server_url_func):
    """
    Adds a handler for a websocket.

    Args:
      url (str): URL string with optional placeholders.
      server_url_func (callable): Converts placeholders (which are passed as
          keyword arguments) to a relative URL for the server websocket to
          proxy.
    """
    def handle(environ, start_response, **kwargs):
      server_url = server_url_func(**kwargs)
      return self._handle(environ, start_response, server_url)

    self._wsgi_handler.add_wsgi_handler(handle, url, "GET")
