#!/usr/bin/env python3

"""
wsgi_file_handler.py

This module provides an asynchronous file handler for serving static files
in an aiohttp-based web application. It defines a single function,
`wsgi_file_handler`, which processes incoming HTTP requests and serves
the requested file.

The file path is retrieved from the request's match_info and is expected
to be relative to the 'static' directory. The function performs several
checks to ensure the file path is valid and accessible, and it handles
various error conditions by returning appropriate HTTP responses.

Functions:
    wsgi_file_handler(request): Asynchronously handles an HTTP request
    to serve a file. Returns an aiohttp.web.Response object containing
    the file content or an error message.

Logging:
    The module uses the `logging` library to log debug, warning, and error
    messages related to file access and request handling.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import logging
import mimetypes
import os

import aiofiles
import aiohttp

from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s,%(msecs)03dZ [%(levelname)8s] (%(filename)s:%(lineno)s) %(message)s')
logger = logging.getLogger(__name__)


async def wsgi_file_handler(request):
    """
    Handle an incoming HTTP request and serve a file.

    The function retrieves the file path from the request's match_info.

    If the file path is invalid or attempts to access forbidden paths, it
    returns a 403 response.

    If the file does not exist, it returns a 404 response.

    Otherwise, it reads the file content asynchronously and streams it back
    in the response body.

    If an error occurs during file reading, it returns a 500 response.

    Args:
        request (aiohttp.web.Request): The incoming HTTP request.

    Returns:
        aiohttp.web.Response: The HTTP response containing the file content
        or an error message.

    Raises:
        aiohttp.web.HTTPException: If an HTTP-related exception occurs.
        Exception: If any other unexpected error occurs.
    """

    try:
        file_path = os.path.join(
            'static', request.match_info.get(
                'file_path', 'index.html'))
        logger.debug("Received request for file: %s", file_path)

        # Check if the file path is valid and does not access forbidden paths
        # aiohttp will not allow forbidden paths to be accessed, so we only
        # need to check if the file exists.
        if not os.path.isfile(file_path):
            logger.warning("File not found: %s", file_path)
            return web.Response(status=404, text="File not found")

        logger.debug("Serving file: %s", file_path)
    except (OSError, ValueError) as e:
        logger.error("Exception occurred while processing the file path: %s", e)
        return web.Response(status=500, text="Internal server error")

    try:
        async with aiofiles.open(file_path, 'rb') as f:
            chunk_size = 8192
            response = web.StreamResponse(
                headers={'Content-Type': mimetypes.guess_type(file_path)[0] or
                         'application/octet-stream'})
            await response.prepare(request)
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                await response.write(chunk)
            await response.write_eof()
            return response
    except aiohttp.web.HTTPException as e:
        logger.error("HTTP exception occurred: %s", e)
        return web.Response(status=500, text="Internal server error")
