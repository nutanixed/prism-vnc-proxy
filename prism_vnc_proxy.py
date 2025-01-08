#!/usr/bin/env python
#
# Copyright (c) 2015 Nutanix Inc. All rights reserved.
#
# Author: gasmith@nutanix.com
#

try:
  import env
except ImportError:
  pass

import gevent.monkey
gevent.monkey.patch_all()

import inspect
import logging
import optparse
import os
import socket
import sys

from wsgi_file_handler import WSGIFileHandler
from wsgi_http_handler import WSGIHttpHandler
from wsgi_prism_websocket_proxy import WSGIPrismWebsocketProxy

log = logging.getLogger(__name__)

def parse_opts():
  """
  Parses command line options.

  Returns:
    optparse options object, or None.
  """
  p = optparse.OptionParser()
  p.set_usage(inspect.cleandoc("""
      %s --prism_hostname=<hostname> --prism_password=<password> [options]

      A small HTTP proxy and frontend for VM VNC websockets.

      This application runs an HTTP server that proxies websocket traffic
      through Prism gateway (specified by --prism_hostname), and provides a
      frontend UI for Acropolis VM VNC websockets in particular.

      The VNC websocket proxy can be accessed directly via the following URL,
      where $vm_uuid is a hex-formatted UUID. The websocket will only be
      responsive if the corresponding VM is up and running.

        /proxy/$vm_uuid

      The VNC UI can be accessed via the following URL scheme. Note that the
      required 'path' parameter encodes the websocket proxy URI. The optional
      'name' parameter can be used to control the page name.

        /console/vnc_auto.html?path=proxy/$vm_uuid&name=$name
      """ % (sys.argv[0],)))
  p.add_option(
      "--bind_address", dest="bind_address", default="")
  p.add_option(
      "--bind_port", dest="bind_port", type="int", default=8080)
  p.add_option(
      "--prism_hostname", dest="prism_hostname")
  p.add_option(
      "--prism_username", dest="prism_username", default="admin")
  p.add_option(
      "--prism_password", dest="prism_password")
  p.add_option(
      "--docroot", dest="docroot",
      default=os.path.join(os.path.dirname(__file__), "static"))

  opts, args = p.parse_args()

  ok = True
  for name in "prism_hostname", "prism_password":
    if getattr(opts, name) is None:
      log.error("The --%s argument is required" % (name,))
      ok = False
  if not ok:
    return None

  if args:
    log.warning("Ignoring unexpected arguments: %s" % (args,))

  return opts

def run_server(server_address, handler, timeout=None, enable_ipv6=False,
               allow_reuse_address=True, max_size=50):
  """
  Creates a gevent WSGI server and runs it forever.

  Args:
    server_address ((str, int)): Server address and port.
    handler (callable): Handle function called when an HTTP request is
        processed.
    timeout (int): Socket timeout.
    enable_ipv6 (bool): Whether to enable IPv6.
    allow_reuse_address (bool): Allow kernel to reuse local socket.
    max_size (int): Maximum number of client connections that can be opened by
        the server at a particular point in time.
  """
  from gevent.pywsgi import WSGIServer, WSGIHandler

  # Disable Nagle on accepted sockets.
  class WsgiSocket(socket.socket):
    def accept(self):
      ret = socket.socket.accept(self)
      ret[0].setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
      return ret

  # Enable keepalive.
  class handler_class(WSGIHandler):
    def __init__(self, *args, **kwargs):
      WSGIHandler.__init__(self, *args, **kwargs)
      self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

  family = socket.AF_INET6 if enable_ipv6 else socket.AF_INET
  sock = WsgiSocket(family, socket.SOCK_STREAM)
  sock.setsockopt(
      socket.SOL_SOCKET, socket.SO_REUSEADDR, int(bool(allow_reuse_address)))
  sock.settimeout(timeout)
  sock.bind(server_address)
  sock.listen(max_size)
  server = WSGIServer(sock, handler, log=open(os.devnull, "w+"),
                      spawn=max_size or "default", handler_class=handler_class)
  server.serve_forever()

def main():
  """
  Main entry point.

  Runs an HTTP server that serves static content and the websocket proxy.

  Returns:
    int: Status code.
  """
  opts = parse_opts()
  if opts is None:
    return 1

  http_handler = WSGIHttpHandler()

  # Add a handler for static content (HTML, js, css, &c.).
  WSGIFileHandler(http_handler).add_handle("/console", opts.docroot)

  # Configure the prism websocket handler. Local requests to /proxy/<vm_uuid>
  # are proxied to $prism/vnc/vm/<vm_uuid>/proxy.
  WSGIPrismWebsocketProxy(
      http_handler,
      opts.prism_hostname,
      opts.prism_username,
      opts.prism_password).add_handler(
          "/proxy/<vm_uuid>",
          lambda vm_uuid: "/vnc/vm/%s/proxy" % (vm_uuid,))

  # Run the server forever.
  run_server((opts.bind_address, opts.bind_port), http_handler.handle)
  return 0

if __name__ == "__main__":
  import sys
  logging.basicConfig(level=logging.INFO)
  sys.exit(main())
