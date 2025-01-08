#!/usr/bin/env python3

"""
demo-ws-client.py

This script demonstrates a simple WebSocket client using the `websockets` library in Python.
The client connects to a WebSocket server running on localhost at port 9998, sends a greeting
message to the server, and prints the response received from the server.

Usage:
    python3 demo-ws-client.py

Dependencies:
    - websockets: Install using `pip install websockets`

Functions:
    - connect(): Asynchronous function that establishes a WebSocket connection, sends a message,
                 and prints the server's response.

Author:
    Jon Kohler (jon@nutanix.com)

Copyright:
    (c) 2025 Nutanix Inc. All rights reserved.
"""

import asyncio
import websockets

async def connect():
    uri = "ws://localhost:9998"
    async with websockets.connect(uri) as websocket:
        print("Connected to the server")
        await websocket.send("Hello, Server!")
        response = await websocket.recv()
        print(f"Received from server: {response}")

asyncio.run(connect())
