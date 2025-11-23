#!/usr/bin/env python3
"""
MCP Client with Streamable HTTP Transport (2024-11-05 Specification)

This client supports:
- HTTP POST for JSON-RPC requests
- SSE for server notifications and progress updates
- Automatic session management
- Async operation
"""

import asyncio
import json
import logging
import sys
import threading
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

import aiohttp
from aiohttp_sse_client import client as sse_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MCP Protocol Version
PROTOCOL_VERSION = "2024-11-05"


@dataclass
class ServerInfo:
    """Server information from initialization"""
    name: str
    version: str
    protocol_version: str
    capabilities: Dict[str, Any]


class MCPClient:
    """
    MCP Client implementing the 2024-11-05 specification
    with Streamable HTTP transport support.
    """

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url.rstrip("/")
        self.session_id: Optional[str] = None
        self.server_info: Optional[ServerInfo] = None
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._sse_task: Optional[asyncio.Task] = None
        self._notification_handlers: Dict[str, List[Callable]] = {}
        self._request_id = 0

        # Client capabilities
        self.capabilities = {
            "roots": {"listChanged": True},
            "sampling": {}
        }

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self) -> ServerInfo:
        """Connect to MCP server and initialize"""
        self._http_session = aiohttp.ClientSession()

        # Initialize connection
        response = await self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": self.capabilities,
            "clientInfo": {
                "name": "mcp-client",
                "version": "1.0.0"
            }
        })

        self.server_info = ServerInfo(
            name=response.get("serverInfo", {}).get("name", "unknown"),
            version=response.get("serverInfo", {}).get("version", "unknown"),
            protocol_version=response.get("protocolVersion", "unknown"),
            capabilities=response.get("capabilities", {})
        )

        logger.info(f"Connected to {self.server_info.name} v{self.server_info.version}")

        # Send initialized notification
        await self._notify("initialized", {})

        return self.server_info

    async def disconnect(self):
        """Disconnect from server"""
        if self._sse_task:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass

        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        logger.info("Disconnected from server")

    def _next_id(self) -> int:
        """Get next request ID"""
        self._request_id += 1
        return self._request_id

    async def _request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for response"""
        if not self._http_session:
            raise RuntimeError("Client not connected")

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {}
        }

        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["X-Session-ID"] = self.session_id

        async with self._http_session.post(
            f"{self.server_url}/mcp",
            json=request,
            headers=headers
        ) as response:
            # Store session ID from response
            if "X-Session-ID" in response.headers:
                self.session_id = response.headers["X-Session-ID"]

            if response.status != 200:
                text = await response.text()
                raise RuntimeError(f"Request failed: {response.status} - {text}")

            result = await response.json()

            if "error" in result:
                error = result["error"]
                raise RuntimeError(f"RPC Error {error['code']}: {error['message']}")

            return result.get("result", {})

    async def _notify(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a JSON-RPC notification (no response expected)"""
        if not self._http_session:
            raise RuntimeError("Client not connected")

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["X-Session-ID"] = self.session_id

        async with self._http_session.post(
            f"{self.server_url}/mcp",
            json=request,
            headers=headers
        ) as response:
            # Notifications may return 204 No Content
            if response.status not in (200, 204):
                text = await response.text()
                raise RuntimeError(f"Notification failed: {response.status} - {text}")

    # === SSE Support ===

    async def start_sse(self):
        """Start SSE connection for server notifications"""
        self._sse_task = asyncio.create_task(self._sse_listener())

    async def _sse_listener(self):
        """Listen for SSE events"""
        headers = {}
        if self.session_id:
            headers["X-Session-ID"] = self.session_id

        try:
            async with sse_client.EventSource(
                f"{self.server_url}/mcp/sse",
                headers=headers
            ) as event_source:
                async for event in event_source:
                    await self._handle_sse_event(event)
        except asyncio.CancelledError:
            logger.debug("SSE listener cancelled")
        except Exception as e:
            logger.error(f"SSE error: {e}")

    async def _handle_sse_event(self, event):
        """Handle incoming SSE event"""
        if event.type == "ping":
            return  # Keepalive

        if event.type == "connection":
            data = json.loads(event.data)
            logger.info(f"SSE connected: session {data.get('sessionId')}")
            return

        if event.type == "message":
            try:
                data = json.loads(event.data)
                method = data.get("method", "")

                # Call registered handlers
                handlers = self._notification_handlers.get(method, [])
                for handler in handlers:
                    try:
                        await handler(data.get("params", {}))
                    except Exception as e:
                        logger.error(f"Handler error for {method}: {e}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid SSE message: {event.data}")

    def on_notification(self, method: str, handler: Callable):
        """Register a handler for a notification type"""
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)

    # === MCP Methods ===

    async def ping(self) -> bool:
        """Ping the server"""
        await self._request("ping", {})
        return True

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        result = await self._request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call a tool"""
        result = await self._request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
        return result

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources"""
        result = await self._request("resources/list", {})
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource"""
        result = await self._request("resources/read", {"uri": uri})
        return result

    async def subscribe_resource(self, uri: str):
        """Subscribe to resource updates"""
        await self._request("resources/subscribe", {"uri": uri})

    async def unsubscribe_resource(self, uri: str):
        """Unsubscribe from resource updates"""
        await self._request("resources/unsubscribe", {"uri": uri})

    async def list_resource_templates(self) -> List[Dict[str, Any]]:
        """List resource templates"""
        result = await self._request("resources/templates/list", {})
        return result.get("resourceTemplates", [])

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts"""
        result = await self._request("prompts/list", {})
        return result.get("prompts", [])

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a prompt"""
        result = await self._request("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })
        return result

    async def set_log_level(self, level: str):
        """Set server log level"""
        await self._request("logging/setLevel", {"level": level})

    async def complete(
        self, ref: Dict[str, Any], argument: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get argument completions"""
        result = await self._request("completion/complete", {
            "ref": ref,
            "argument": argument
        })
        return result.get("completion", {})


# === Interactive CLI ===

async def interactive_mode(client: MCPClient):
    """Interactive command-line interface"""
    print("\nMCP Client Interactive Mode")
    print("=" * 50)
    print("Commands:")
    print("  /tools              - List available tools")
    print("  /call <name> [json] - Call a tool")
    print("  /resources          - List resources")
    print("  /read <uri>         - Read a resource")
    print("  /subscribe <uri>    - Subscribe to resource")
    print("  /prompts            - List prompts")
    print("  /prompt <name> [json] - Get a prompt")
    print("  /ping               - Ping server")
    print("  /status             - Read server status")
    print("  /help               - Show this help")
    print("  /quit               - Exit")
    print("=" * 50)

    # Set up notification handlers
    async def on_progress(params):
        progress = params.get("progress", 0)
        total = params.get("total", 100)
        message = params.get("message", "")
        print(f"\r[Progress: {progress}/{total}] {message}", end="", flush=True)
        if progress >= total:
            print()  # New line when complete

    async def on_resource_updated(params):
        uri = params.get("uri", "")
        print(f"\n[Resource Updated: {uri}]")

    client.on_notification("notifications/progress", on_progress)
    client.on_notification("notifications/resources/updated", on_resource_updated)

    # Start SSE listener
    await client.start_sse()

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("\nmcp> ").strip()
            )

            if not user_input:
                continue

            if user_input in ["/quit", "/exit", "/q"]:
                break

            elif user_input == "/help":
                print("Commands: /tools, /call, /resources, /read, /subscribe,")
                print("          /prompts, /prompt, /ping, /status, /quit")

            elif user_input == "/ping":
                await client.ping()
                print("Pong!")

            elif user_input == "/tools":
                tools = await client.list_tools()
                print(f"\nAvailable Tools ({len(tools)}):")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")

            elif user_input.startswith("/call "):
                parts = user_input[6:].split(None, 1)
                name = parts[0]
                args = json.loads(parts[1]) if len(parts) > 1 else {}

                print(f"Calling tool: {name}")
                result = await client.call_tool(name, args)

                if result.get("isError"):
                    print(f"Error: {result}")
                else:
                    content = result.get("content", [])
                    for item in content:
                        if item.get("type") == "text":
                            print(f"Result: {item.get('text')}")

            elif user_input == "/resources":
                resources = await client.list_resources()
                print(f"\nAvailable Resources ({len(resources)}):")
                for res in resources:
                    print(f"  - {res['uri']}: {res['name']}")

            elif user_input.startswith("/read "):
                uri = user_input[6:].strip()
                result = await client.read_resource(uri)
                contents = result.get("contents", [])
                for content in contents:
                    print(f"\n[{content.get('mimeType', 'text/plain')}]")
                    print(content.get("text", ""))

            elif user_input.startswith("/subscribe "):
                uri = user_input[11:].strip()
                await client.subscribe_resource(uri)
                print(f"Subscribed to: {uri}")

            elif user_input == "/prompts":
                prompts = await client.list_prompts()
                print(f"\nAvailable Prompts ({len(prompts)}):")
                for prompt in prompts:
                    print(f"  - {prompt['name']}: {prompt['description']}")

            elif user_input.startswith("/prompt "):
                parts = user_input[8:].split(None, 1)
                name = parts[0]
                args = json.loads(parts[1]) if len(parts) > 1 else {}

                result = await client.get_prompt(name, args)
                messages = result.get("messages", [])
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", {})
                    text = content.get("text", "") if isinstance(content, dict) else content
                    print(f"\n[{role}]: {text}")

            elif user_input == "/status":
                result = await client.read_resource("server://status")
                contents = result.get("contents", [])
                if contents:
                    print("\nServer Status:")
                    print(contents[0].get("text", ""))

            else:
                print(f"Unknown command: {user_input}")
                print("Type /help for available commands")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


async def demo_mode(client: MCPClient):
    """Run a demonstration of MCP features"""
    print("\nMCP Client Demo Mode")
    print("=" * 50)

    # Set up progress handler
    async def on_progress(params):
        progress = params.get("progress", 0)
        total = params.get("total", 100)
        message = params.get("message", "")
        bar_len = 30
        filled = int(bar_len * progress / total)
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r  [{bar}] {progress}/{total} {message}", end="", flush=True)
        if progress >= total:
            print()

    client.on_notification("notifications/progress", on_progress)
    await client.start_sse()

    # Give SSE time to connect
    await asyncio.sleep(0.5)

    print("\n1. Server Info:")
    print(f"   Name: {client.server_info.name}")
    print(f"   Version: {client.server_info.version}")
    print(f"   Protocol: {client.server_info.protocol_version}")

    print("\n2. Ping Test:")
    await client.ping()
    print("   Pong! Server is responsive.")

    print("\n3. Available Tools:")
    tools = await client.list_tools()
    for tool in tools[:3]:  # Show first 3
        print(f"   - {tool['name']}")
    if len(tools) > 3:
        print(f"   ... and {len(tools) - 3} more")

    print("\n4. Tool Calls:")
    # Get time
    result = await client.call_tool("get_current_time")
    print(f"   Time: {result['content'][0]['text']}")

    # Add a note
    result = await client.call_tool("add_note", {
        "content": "Demo note from MCP client",
        "tags": ["demo", "test"]
    })
    print(f"   Note: {result['content'][0]['text']}")

    # Calculate
    result = await client.call_tool("calculate", {
        "operation": "multiply",
        "a": 7,
        "b": 8
    })
    print(f"   Calc: {result['content'][0]['text']}")

    print("\n5. Long-Running Task (with progress):")
    result = await client.call_tool("long_running_task", {
        "steps": 5,
        "delay": 0.3
    })
    print(f"   {result['content'][0]['text']}")

    print("\n6. Resources:")
    resources = await client.list_resources()
    for res in resources:
        print(f"   - {res['uri']}")

    print("\n7. Read Server Status:")
    result = await client.read_resource("server://status")
    status = json.loads(result["contents"][0]["text"])
    print(f"   Status: {status['status']}")
    print(f"   Notes: {status['notes_count']}")
    print(f"   Counter: {status['counter']}")

    print("\n8. Prompts:")
    prompts = await client.list_prompts()
    for prompt in prompts:
        print(f"   - {prompt['name']}: {prompt['description']}")

    print("\n9. Get Greeting Prompt:")
    result = await client.get_prompt("greeting", {
        "name": "Developer",
        "style": "enthusiastic"
    })
    text = result["messages"][0]["content"]["text"]
    print(f"   {text}")

    print("\n" + "=" * 50)
    print("Demo completed!")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Client")
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Server URL"
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "demo"],
        default="interactive",
        help="Client mode"
    )

    args = parser.parse_args()

    async with MCPClient(args.server) as client:
        if args.mode == "demo":
            await demo_mode(client)
        else:
            await interactive_mode(client)


if __name__ == "__main__":
    asyncio.run(main())
