"""
This module contains unit tests for the `prism_vnc_proxy` module using the
pytest framework.

Tests included:
- `test_parse_opts`: Verifies that the `parse_opts` function correctly parses
    command-line arguments.
- `test_parse_opts_missing_required`: Ensures that `parse_opts` raises a
    SystemExit when required arguments are missing.
- `test_main`: Tests the `main` function of the `prism_vnc_proxy` module.
- `test_main_opts_none`: Ensures that the `main` function returns 1 when
    options parsing fails.

Logging:
    Logging is configured to output debug information to assist in tracing the
    execution of tests.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import logging

import pytest

from prism_vnc_proxy import parse_opts, main

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_parse_opts(monkeypatch):
    """
    Test the parse_opts function to ensure it correctly parses command-line
    arguments.

    This test uses the monkeypatch fixture to temporarily set the value of
    sys.argv and then calls the parse_opts function to parse these arguments.
    It verifies that the parsed options match the expected values.

    Args:
        monkeypatch: pytest's monkeypatch fixture to modify sys.argv.

    Asserts:
        - opts.prism_hostname is 'test_hostname'
        - opts.prism_password is 'test_password'
        - opts.bind_address is an empty string
        - opts.bind_port is 8080
        - opts.prism_username is 'admin'
    """
    logger.debug("Starting test_parse_opts")
    monkeypatch.setattr('sys.argv', [
        'prism_vnc_proxy.py',
        '--prism_hostname', 'test_hostname',
        '--prism_password', 'test_password'
    ])
    opts = parse_opts()
    logger.debug("Parsed options: %s", opts)
    assert opts.prism_hostname == 'test_hostname'
    assert opts.prism_password == 'test_password'
    assert opts.bind_address == ''
    assert opts.bind_port == 8080
    assert opts.prism_username == 'admin'
    logger.debug("Finished test_parse_opts")


def test_parse_opts_missing_required(monkeypatch):
    """
    Test the parse_opts function to ensure it raises a SystemExit exception
    when required command-line arguments are missing.

    This test uses the monkeypatch fixture to modify sys.argv to simulate
    running the script with missing required arguments.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture to modify
                                          sys.argv.

    Raises:
        SystemExit: Expected to be raised by parse_opts() due to missing
                    required arguments.
    """
    logger.debug("Starting test_parse_opts_missing_required")
    monkeypatch.setattr('sys.argv', [
        'prism_vnc_proxy.py',
        '--prism_hostname', 'test_hostname'
    ])
    with pytest.raises(SystemExit):
        parse_opts()
    logger.debug("Finished test_parse_opts_missing_required")


async def test_main(monkeypatch):
    """
    Test the main function of the prism_vnc_proxy module.

    This test uses the monkeypatch fixture to modify the command line
    arguments and the behavior of the web.run_app function. It verifies that
    the main function returns 0 when executed with the provided arguments.

    Args:
        monkeypatch: A pytest fixture that allows modifying or simulating
                     attributes and functions.

    Assertions:
        Asserts that the main function returns 0.
    """
    logger.debug("Starting test_main")
    monkeypatch.setattr('sys.argv', [
        'prism_vnc_proxy.py',
        '--prism_hostname', 'test_hostname',
        '--prism_password', 'test_password'
    ])
    monkeypatch.setattr(
        'prism_vnc_proxy.web.run_app',
        lambda app,
        host,
        port: None)
    result = main()
    logger.debug("Main function result: %d", result)
    assert result == 0
    logger.debug("Finished test_main")


def test_main_opts_none(monkeypatch):
    """
    Test the main function to ensure it returns 1 when options parsing fails.

    This test uses the monkeypatch fixture to modify the parse_opts function
    to return None, simulating a failure in options parsing.

    Args:
        monkeypatch: A pytest fixture that allows modifying or simulating
                     attributes and functions.

    Assertions:
        Asserts that the main function returns 1.
    """
    logger.debug("Starting test_main_opts_none")
    monkeypatch.setattr('prism_vnc_proxy.parse_opts', lambda: None)
    result = main()
    logger.debug("Main function result when opts is None: %d", result)
    assert result == 1
    logger.debug("Finished test_main_opts_none")
