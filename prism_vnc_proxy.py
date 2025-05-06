#!/usr/bin/env python3

"""
prism_vnc_proxy.py

HTTPS frontend for the VNC proxy with optional SSL support.
"""

import argparse
import inspect
import logging
import os
import ssl
import sys

from aiohttp import web

from wsgi_file_handler import wsgi_file_handler
from wsgi_prism_websocket_proxy import WSGIPrismWebsocketProxy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s,%(msecs)03dZ [%(levelname)8s] (%(filename)s:%(lineno)s) %(message)s'
)
log = logging.getLogger(__name__)


def parse_opts() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HTTP/HTTPS proxy + frontend for Prism VNC websockets.",
        usage=inspect.cleandoc("""
            %(prog)s --prism_hostname=<host> --prism_password=<password> [options]
        """)
    )
    parser.add_argument("--bind_address", default="", help="Address to bind to (default: all interfaces)")
    parser.add_argument("--bind_port", type=int, default=8080, help="Port to bind to (default: 8080)")
    parser.add_argument("--prism_hostname", required=True, help="Prism hostname or IP")
    parser.add_argument("--prism_username", default="admin", help="Prism username (default: admin)")
    parser.add_argument("--prism_password", required=True, help="Prism password")
    parser.add_argument("--ssl_cert", help="Path to SSL certificate (PEM format)")
    parser.add_argument("--ssl_key", help="Path to SSL private key (PEM format)")
    parser.add_argument(
        "--use_pc",
        action="store_true",
        help="Use Prism Central (instead of Prism Element)"
    )
    return parser.parse_args()


def main() -> int:
    opts = parse_opts()

    proxy = WSGIPrismWebsocketProxy(
        host=opts.prism_hostname,
        user=opts.prism_username,
        password=opts.prism_password,
        use_pc=opts.use_pc
    )

    app = web.Application()
    app.router.add_get('/console/{file_path:.*}', wsgi_file_handler)
    app.router.add_get('/proxy/{vm_uuid}', proxy.prism_websocket_handler)

    bind_address = opts.bind_address or '0.0.0.0'

    ssl_context = None
    if opts.ssl_cert and opts.ssl_key:
        log.info("Configuring SSL with cert: %s and key: %s", opts.ssl_cert, opts.ssl_key)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=opts.ssl_cert, keyfile=opts.ssl_key)

    log.info("Starting aiohttp server on %s:%s", bind_address, opts.bind_port)
    web.run_app(app, host=bind_address, port=opts.bind_port, ssl_context=ssl_context)

    return 0


if __name__ == "__main__":
    assert sys.version_info[:2] >= (3, 9), "Requires Python 3.9+"
    assert "VIRTUAL_ENV" in os.environ, "Activate your virtualenv"
    log.info("Starting Python %s", sys.version.split()[0])
    sys.exit(main())