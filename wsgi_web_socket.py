# Unless otherwise noted, the files in Eventlet are under the following MIT license:
#
# Copyright (c) 2005-2006, Bob Ippolito
# Copyright (c) 2007-2010, Linden Research, Inc.
# Copyright (c) 2008-2010, Eventlet Contributors (see AUTHORS)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import base64
import collections
import errno
import hashlib
import logging
import re
import string
import struct
from socket import error as SocketError
from websocket import WebSocket

from gevent import socket

log = logging.getLogger(__name__)

ACCEPTABLE_CLIENT_ERRORS = set((errno.ECONNRESET, errno.EPIPE))

__all__ = ["WebSocketWSGI" ]

class WebSocketWSGI(object):
  """Wraps a websocket handler function in a WSGI application.

  Use it like this::

    @websocket.WebSocketWSGI
    def my_handler(ws):
      from_browser = ws.wait()
      ws.send("from server")

  The single argument to the function will be an instance of
  :class:`WebSocket`.  To close the socket, simply return from the
  function.  Note that the server will log the websocket request at
  the time of closure.
  """

  SUPPORTED_VERSIONS = ("13", "8", "7")
  GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

  def __init__(self, handler):
    self.handler = handler
    self.protocol_version = None

  def __call__(self, environ, start_response):
    connection_value = re.split(
        ",\s*",
        environ.get("HTTP_CONNECTION", '').lower())
    if not ('upgrade' in connection_value and
            environ.get('HTTP_UPGRADE', '').lower() == 'websocket'):
      start_response('400 Bad Request', [('Connection','close')])
      return []

    if "HTTP_SEC_WEBSOCKET_VERSION" not in environ:
      start_response(
          "426 Upgrade Required",
          [("Sec-WebSocket-Version", ", ".join(self.SUPPORTED_VERSIONS))])
      return ["Bad protocol version"]
    elif (environ["HTTP_SEC_WEBSOCKET_VERSION"] not in
          self.SUPPORTED_VERSIONS):
      msg = ("Unsupported WebSocket Version: %s" %
             environ["HTTP_SEC_WEBSOCKET_VERSION"])
      log.warning(msg)
      start_response(
        "400 Bad Request",
        [("Sec-WebSocket-Version", ", ".join(self.SUPPORTED_VERSIONS))])
      return [ msg ]

    key = environ.get("HTTP_SEC_WEBSOCKET_KEY", "").strip()
    if not key:
      msg = "Sec-Websocket-Key header is missing/empty"
      log.warning(msg)
      start_response("400 Bad Request", [])
      return [ msg ]

    try:
      key_len = len(base64.b64decode(key))
    except TypeError:
      msg = "Invalid key: %s" % key
      log.warning(msg)
      start_response("400 Bad Request", [])
      return [ msg ]

    if key_len != 16:
      # 5.2.1 (3).
      msg = "Key %s is an unexpected length" % key
      log.warning(msg)
      start_response("400 Bad Request", [])
      return [ msg ]

    # Get the underlying socket and wrap a WebSocket class around it
    sock = environ['wsgi.input'].rfile._sock
    ws = WebSocket(sock, environ)
    ws.sock = sock

    environ["wsgi.websocket_version"] = (
        environ["HTTP_SEC_WEBSOCKET_VERSION"])
    environ["wsgi.websocket"] = ws

    headers = [
      ("Upgrade", "websocket"),
      ("Connection", "Upgrade"),
      ("Sec-WebSocket-Accept", base64.b64encode(
        hashlib.sha1(key + self.GUID).digest()))
    ]

    # Prefer binary if the client supports it.
    protocols = environ.get("HTTP_SEC_WEBSOCKET_PROTOCOL", "").split(", ")
    protocol = "base64"
    if "binary" in protocols:
      protocol = "binary"

    headers.append(("Sec-WebSocket-Protocol", protocol))

    log.debug("WebSocket request accepted, switching protocols")
    handshake_reply = "HTTP/1.1 101 Switching Protocols\r\n"
    for header_key, header_value in headers:
      handshake_reply += "%s: %s\r\n" % (header_key, header_value)
    handshake_reply += "\r\n"

    sock.sendall(handshake_reply)
    try:
      self.handler(ws)
    except socket.error as e:
      errno = e.errno
      if not isinstance(errno, int) and errno is not None:
        # see http://bugs.python.org/issue6471
        errno = e.strerror.errno
      if errno not in ACCEPTABLE_CLIENT_ERRORS:
        raise
    # Make sure we send the closing frame
    ws.close()
    return []
