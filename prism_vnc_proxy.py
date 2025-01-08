#!/usr/bin/env python3

"""
prism_vnc_proxy.py

This module implements a small HTTP proxy and frontend for VM VNC websockets.
It uses aiohttp to run an HTTP server that proxies websocket traffic through
a Prism gateway and provides a frontend UI for Acropolis VM VNC websockets.

Classes:
  WSGIPrismWebsocketProxy: Handles websocket proxying to the Prism gateway.

Functions:
  parse_opts(): Parses command line options and returns an optparse options object.
  main(): Main entry point for the VNC proxy server. Configures the WebSocket proxy
      for VNC connections and starts an HTTP server using aiohttp.
  
Usage:
  Run this script with the required command-line arguments to start the VNC proxy server.
  Example:
    python prism_vnc_proxy.py --prism_hostname=<hostname> --prism_password=<password> [options]
  
Command-line Options:
  --bind_address: Address to bind the HTTP server to (default: "").
  --bind_port: Port to bind the HTTP server to (default: 8080).
  --prism_hostname: Hostname of the Prism gateway.
  --prism_username: Username for the Prism gateway (default: "admin").
  --prism_password: Password for the Prism gateway.

Endpoints:
  /proxy/$vm_uuid: Proxies websocket traffic to the VNC server for the specified VM UUID.
  /console/vnc_auto.html?path=proxy/$vm_uuid&name=$name: Provides a frontend UI for the VNC websocket.

Logging:
  Logs information and errors to the console using the logging module.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

from aiohttp import web

import inspect
import logging
import optparse
import os
import socket
import sys

from wsgi_file_handler import wsgi_file_handler
from wsgi_prism_websocket_proxy import WSGIPrismWebsocketProxy

logging.basicConfig(level=logging.INFO)
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
      where $vm_uuid is a hex-formatted UUID4. The websocket will only be
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

def main():
  """
  Main entry point for the VNC proxy server.
  
  This function parses command-line options, configures the WebSocket proxy
  for VNC connections, and starts an HTTP server using aiohttp. The server
  serves static content and proxies WebSocket connections to the VNC server.
  The server listens on the address and port specified by the command-line
  options.
  
  Returns:
    int: Status code. Returns 1 if options parsing fails, otherwise 0.
  """
  opts = parse_opts()
  if opts is None:
    return 1

  # Configure the prism websocket handler. Local requests to /proxy/<vm_uuid>
  # are proxied to $prism/vnc/vm/<vm_uuid>/proxy.
  proxy_obj = WSGIPrismWebsocketProxy(
    opts.prism_hostname,
    opts.prism_username,
    opts.prism_password)

  # Define the aiohttp app server.
  app = web.Application()
  
  # Add the file handler for serving static content.
  app.router.add_get('/console/{file_path:.*}', wsgi_file_handler)
  
  # Add the websocket handler for the VNC proxy.
  app.add_routes([web.get('/proxy/{vm_uuid}', proxy_obj.prism_websocket_handler)])

  log.info("Starting aiohttp server")
  web.run_app(app, host=opts.bind_address, port=opts.bind_port)
  return 0

if __name__ == "__main__":
  import sys
  sys.exit(main())
