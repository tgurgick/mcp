#!/usr/bin/env python3
"""
MCP Server with Stdio Transport (2024-11-05 Specification)

This implementation provides stdio transport for local process communication,
commonly used when MCP servers are spawned as subprocesses.

Usage:
    python mcp_stdio_server.py

Then send JSON-RPC messages via stdin and receive responses via stdout.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, Optional

# Import the core server logic
from mcp_server import MCPServer, MCPSession, PROTOCOL_VERSION

# Configure logging to stderr (stdout is for protocol messages)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class StdioTransport:
    """
    Stdio Transport for MCP

    - Reads JSON-RPC messages from stdin (line-delimited)
    - Writes JSON-RPC responses to stdout (line-delimited)
    """

    def __init__(self, server: MCPServer):
        self.server = server
        self.session = MCPSession(session_id="stdio-session")
        self.server.sessions["stdio-session"] = self.session
        self._notification_queue: asyncio.Queue = asyncio.Queue()

    async def _read_message(self) -> Optional[Dict[str, Any]]:
        """Read a JSON-RPC message from stdin"""
        loop = asyncio.get_event_loop()

        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                return None

            line = line.strip()
            if not line:
                return None

            return json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return {"error": "parse_error"}
        except Exception as e:
            logger.error(f"Error reading stdin: {e}")
            return None

    def _write_message(self, message: Dict[str, Any]):
        """Write a JSON-RPC message to stdout"""
        try:
            line = json.dumps(message) + "\n"
            sys.stdout.write(line)
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error writing to stdout: {e}")

    async def _notification_sender(self):
        """Send queued notifications to stdout"""
        while True:
            try:
                notification = await self._notification_queue.get()
                self._write_message(notification)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error sending notification: {e}")

    async def run(self):
        """Main loop - read requests, process, write responses"""
        logger.info("MCP Stdio Server started")
        logger.info(f"Protocol version: {PROTOCOL_VERSION}")

        # Set up session's notification queue
        self.session.sse_queue = self._notification_queue

        # Start notification sender
        notification_task = asyncio.create_task(self._notification_sender())

        try:
            while True:
                message = await self._read_message()

                if message is None:
                    logger.info("EOF received, shutting down")
                    break

                if "error" in message:
                    self._write_message({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    })
                    continue

                # Process request
                response = await self.server.handle_request(message, self.session)

                # Send response (if not a notification)
                if response is not None:
                    self._write_message(response)

        except KeyboardInterrupt:
            logger.info("Interrupted, shutting down")
        finally:
            notification_task.cancel()
            try:
                await notification_task
            except asyncio.CancelledError:
                pass


async def main():
    """Main entry point"""
    server = MCPServer(name="mcp-stdio-server")
    transport = StdioTransport(server)
    await transport.run()


if __name__ == "__main__":
    asyncio.run(main())
