#
# Copyright (c) 2014 Nutanix Inc. All rights reserved.
#
# Author: robert@nutanix.com
#
# Module defines a WSGI handler object that can be passed to a WSGI server
# instance.
#
# Example(eventlet WSGI server):
#   # Create handler.
#   wsgi_handler = WSGIHttpHandler(..)
#
#   # Add function handlers.
#   wsgi_handler.add_wsgi_handler(func, url)
#
#   eventlet.server(sock, wsgi_handler.handle)

import logging
import os
import re
import select
import threading
import time
import traceback

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule

log = logging.getLogger(__name__)

class WSGIHttpHandler(object):

  @staticmethod
  def default_response_headers(content_type="text/plain"):
    """
    Useful method for filling in default headers for responses. Returns a list
    of tuples: (Header name, Header value).

    Returns:
      List of tuples [(str, str)]
    """
    time_str = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    headers = [
      ("Content-type", content_type),
      ("Cache-control", "no-cache"),
      ("Expires", time_str)
    ]
    return headers

  def __init__(self):
    self.__url_map = Map()

  def add_wsgi_handler(self, handler, url, method):
    """
    Method that registers a WSGI handler function for a particular URL.

    Args:
      handler(func): Function that will handle the WSGI request.
      url (str): URL to handle.
      methods(str): HTTP method.
    """
    rule = Rule(url, methods=[ method ], endpoint=handler)
    self.__url_map.add(rule)

  def __send_error(self, log_level, log_msg, http_error_status,
                   start_response):
    """
    Helper for writing a log messaging and returning an HTTP error status back
    to the client.
    """
    log_level(log_msg)
    return self.__send_response(start_response, http_error_status, [], log_msg)

  def __send_response(self, start_response, status, headers, body):
    """
    Sends a response back to the client.
    """
    start_response(str(status), headers)
    return [ body ]

  def handle(self, environ, start_response):
    """
    Entry point for all HTTP requests. This function will forward the request
    to the appropriate handler.
    """
    # Wrap each start_response with a check to make sure that if we are trying
    # upgrade a connection, we always issue a connection close after we are
    # finished. The reason for this is if we do not issue a connection close
    # and we mistakenly go into a handler that does not properly handle the
    # connection the client may keep the connection open.
    def start_response_wrapper(http_status, headers):
      connection_req_parts = re.split(r",\s*",
                                      environ.get("HTTP_CONNECTION", ""))
      connection_req_parts = map(lambda conn_param: conn_param.lower(),
                                 connection_req_parts)

      if "upgrade" in connection_req_parts:
        resp_headers = dict([ (header_name.lower(), header_value.lower())
                              for header_name, header_value in headers ])
        if "connection" not in resp_headers:
          resp_headers["connection"] = "close"
        elif not re.search(r"close", resp_headers["connection"]):
          resp_headers["connection"] += ", close"

        headers = [ (header_name, header_value)
                    for header_name, header_value in resp_headers.iteritems() ]
      start_response(http_status, headers)

    adapter = self.__url_map.bind_to_environ(environ)
    try:
      endpoint, args = adapter.match()
    except HTTPException as ex:
      return ex(environ, start_response_wrapper)

    try:
      return endpoint(environ, start_response_wrapper, **args)
    except Exception:
      log.error("".join(traceback.format_exc()))
      raise
