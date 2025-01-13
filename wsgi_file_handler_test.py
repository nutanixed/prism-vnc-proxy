"""
This module contains unit tests for the WSGI file handler using the aiohttp
framework.

The tests are designed to verify the following scenarios:
1. File Not Found: Ensures that a request for a non-existent file returns a
    404 status code with the message "File not found".
2. Forbidden Path: Ensures that requests for forbidden paths (e.g., paths
    containing "..") return a 404 status code.
3. Serve File: Ensures that a valid file request returns a 200 status code
    and serves the correct file content.

Classes:
     TestWSGIFileHandler: AioHTTPTestCase subclass that sets up the application
     and contains the test methods.

Functions:
     get_application: Sets up the aiohttp web application with the WSGI file
        handler route.
     test_file_not_found: Tests the scenario where a requested file does not
        exist.
     test_forbidden_path: Tests the scenario where a requested path is
        forbidden.
     test_serve_file: Tests the scenario where a valid file is requested and
        served.

Logging:
     Configured to log at the INFO level. Debug logs are used within test
     methods to trace the execution flow.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import os
import logging

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from aiofiles import open as aio_open
from wsgi_file_handler import wsgi_file_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestWSGIFileHandler(AioHTTPTestCase):
    """
    TestWSGIFileHandler is a test case for the WSGI file handler using
    AioHTTPTestCase.

    This class contains the following test methods:
    - test_file_not_found: Tests the scenario where a requested file does not
      exist.
    - test_forbidden_path: Tests the scenario where a forbidden path is
      requested.
    - test_serve_file: Tests the scenario where a file is successfully served.

    Each test method sends an HTTP GET request to the application and asserts
    the expected response status and content.
    """

    async def get_application(self):
        app = web.Application()
        app.router.add_get('/{file_path:.*}', wsgi_file_handler)
        return app

    async def test_file_not_found(self):
        """
        Test the scenario where a requested file is not found.

        This test simulates a GET request to a nonexistent file and verifies
        that the server responds with a 404 status code and the appropriate
        error message.

        Steps:
        1. Send a GET request to a nonexistent file.
        2. Assert that the response status code is 404.
        3. Assert that the response text is "File not found".

        Logs:
        - Logs the start and successful completion of the test.

        Raises:
        - AssertionError: If the response status code is not 404 or the
          response text is not "File not found".
        """
        logger.debug("Testing file not found scenario")
        request = await self.client.request("GET", "/nonexistent_file.txt")
        assert request.status == 404
        text = await request.text()
        assert text == "File not found"
        logger.debug("File not found test passed")

    async def test_forbidden_path(self):
        """
        Test the scenario where a forbidden path is requested.

        This test simulates a request to a forbidden path (e.g.,
        '/../forbidden.txt') and verifies that the server responds with a 404
        status code instead of a 403.

        The aiohttp framework does not allow forbidden paths, hence the
        expected response is a 404 Not Found.

        Assertions:
            - The response status code should be 404.
        """
        logger.debug("Testing forbidden path scenario")
        request = await self.client.request("GET", "/../forbidden.txt")
        # Forbidden paths are not allowed by aiohttp, so we should get
        # a 404 instead of a 403.
        assert request.status == 404
        logger.debug("Forbidden path test passed")

    async def test_serve_file(self):
        """
        Test the file serving functionality of the application.

        This test creates a test file, serves it via a GET request, and
        verifies that the content of the served file matches the expected
        content. After the test, the created test file is removed.

        Steps:
        1. Create a test file with predefined content.
        2. Make a GET request to serve the test file.
        3. Verify that the response status is 200 (OK).
        4. Verify that the content of the served file matches the expected
           content.
        5. Remove the test file after the test.

        Raises:
            AssertionError: If the response status is not 200 or the content
                    of the served file does not match the expected
                    content.
        """
        logger.debug("Testing serve file scenario")
        file_path = os.path.join('static', 'test_file.txt')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        async with aio_open(file_path, 'w') as f:
            await f.write("This is a test file.")

        request = await self.client.request("GET", "/test_file.txt")
        assert request.status == 200
        text = await request.text()
        assert text == "This is a test file."
        logger.debug("Serve file test passed")

        os.remove(file_path)
        logger.debug("Test file removed")
