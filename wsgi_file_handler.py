#
# Copyright (c) 2014 Nutanix Inc. All rights reserved.
#
# Author: robert@nutanix.com
#
# Defines a WSGI handler that can serve files.
#
# Example:
#   file_handler = WSGIFileHandler(http_handler)
#
#   file_handler.add_handle(handle_url, docroot)

from functools import partial
import logging
import mimetypes
import os

from wsgi_http_handler import WSGIHttpHandler

log = logging.getLogger(__name__)

class WSGIFileHandler(object):

  READ_SIZE = 1024 * 1024

  def __init__(self, wsgi_handler):
    self.__wsgi_handler = wsgi_handler

  def add_handle(self, handle_url, docroot):
    """
    Adds a handle for files under a document root.

    Args:
      handle_url (str): URL for the handle.
      docroot (str): Root path in the local filesystem.
    """
    def handle(environ, start_response, subpath):
      file_path = os.path.join(docroot, subpath)
      file_path = os.path.abspath(file_path)

      # Prevent escaping outside of docroot.
      if os.path.relpath(file_path, docroot).startswith(".."):
        msg = "Path %s is outside of docroot %s" % (file_path, docroot)
        log.error(msg)
        start_response("403 Forbidden", [])
        return [ msg ]

      if not os.path.exists(file_path):
        msg = "File %s does not exist" % file_path
        log.error(msg)
        start_response("404 Not Found", [])
        return [ msg ]

      try:
        type, encoding = mimetypes.guess_type(file_path)
        content_type = type or "text/plain"
        headers = WSGIHttpHandler.default_response_headers(content_type)

        start_response("200 OK", headers)
        read_func = partial(open(file_path).read, self.READ_SIZE)
        return iter(read_func, "")
      except IOError as ex:
        msg = "Failed to read file %s: %s" % (file_path, str(ex))
        log.error(msg)
        start_response("500 Internal Server Error", [])
        return [ msg ]

    self.__wsgi_handler.add_wsgi_handler(
        handle,
        os.path.join(handle_url, "<path:subpath>"),
        "GET")
