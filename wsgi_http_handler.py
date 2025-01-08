#!/usr/bin/env python3
#
# Copyright (c) 2025 Nutanix Inc. All rights reserved.
#
# Author: jon@nutanix.com
#

from aiohttp import web
import logging

logger = logging.getLogger(__name__)

class WSGIHttpHandler:
    """
    WSGIHttpHandler is an asynchronous HTTP handler that adapts a WSGI
    application to be used with aiohttp.

    Attributes:
        wsgi_app (callable): The WSGI application to be handled.

    Methods:
        __init__(wsgi_app):
            Initializes the WSGIHttpHandler with the given WSGI application.

        __call__(request):
            Asynchronously handles an incoming HTTP request, converts it to
            a WSGI environment, calls the WSGI application, and writes the
            response back to the client.

        _create_environ(request):
            Creates a WSGI environment dictionary from the aiohttp request.

        _start_response(response):
            Returns a start_response callable that sets the status and header
            on the aiohttp response.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app 

    async def __call__(self, request):
        try:
            logger.info(f"Handling request: {request.method} {request.path}")
            environ = self._create_environ(request)
            response = web.StreamResponse()
            result = self.wsgi_app(environ, self._start_response(response))
            await response.prepare(request)
            if isinstance(result, list):
                for data in result:
                    await response.write(data)
            else:
                async for data in result:
                    await response.write(data)
            await response.write_eof()
            logger.info(f"Finished handling request: {request.method} {request.path}")
            return response
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return web.Response(status=500, text="Internal Server Error")

    def _create_environ(self, request):
        try:
            environ = {
                'REQUEST_METHOD': request.method,
                'SCRIPT_NAME': '',
                'PATH_INFO': request.path,
                'QUERY_STRING': request.query_string,
                'CONTENT_TYPE': request.content_type,
                'CONTENT_LENGTH': request.content_length,
                'SERVER_NAME': request.host.split(':')[0],
                'SERVER_PORT': request.host.split(':')[1] if ':' in request.host else '80',
                'SERVER_PROTOCOL': request.version,
                'wsgi.version': (1, 0),
                'wsgi.url_scheme': request.scheme,
                'wsgi.input': request.content,
                'wsgi.errors': request.app.logger,
                'wsgi.multithread': False,
                'wsgi.multiprocess': False,
                'wsgi.run_once': False,
            }
            logger.debug(f"Created WSGI environ: {environ}")
            return environ
        except Exception as e:
            logger.error(f"Error creating WSGI environ: {e}")
            raise

    def _start_response(self, response):
        def start_response(status, response_headers, exc_info=None):
            try:
                logger.info(f"Starting response with status: {status}")
                response.set_status(int(status.split()[0]))
                for header in response_headers:
                    response.headers[header[0]] = header[1]
                logger.debug(f"Response headers set: {response_headers}")
            except Exception as e:
                logger.error(f"Error in start_response: {e}")
                raise
        return start_response
