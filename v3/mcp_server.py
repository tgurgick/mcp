#!/usr/bin/env python3
"""
MCP Server with Streamable HTTP Transport (2024-11-05 Specification)

This implementation provides:
- Streamable HTTP transport (POST for requests, SSE for streaming responses)
- Proper MCP protocol compliance
- Tools, Resources, Prompts support
- Progress notifications for long-running operations
- Resource subscriptions
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from aiohttp import web
from aiohttp_sse import sse_response
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MCP Protocol Version (official specification)
PROTOCOL_VERSION = "2024-11-05"

# JSON-RPC Error Codes
class ErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPSession:
    """Represents an MCP client session"""
    session_id: str
    client_info: Dict[str, Any] = field(default_factory=dict)
    client_capabilities: Dict[str, Any] = field(default_factory=dict)
    initialized: bool = False
    subscribed_resources: Set[str] = field(default_factory=set)
    sse_queue: Optional[asyncio.Queue] = None


class MCPServer:
    """
    MCP Server implementing the 2024-11-05 specification
    with Streamable HTTP transport support.
    """

    def __init__(self, name: str = "mcp-server", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.sessions: Dict[str, MCPSession] = {}

        # Server state
        self.counter = 0
        self.notes: List[Dict[str, Any]] = []

        # Registered tools, resources, prompts
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._resource_templates: List[Dict[str, Any]] = []
        self._prompts: Dict[str, Dict[str, Any]] = {}

        # Server capabilities
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True},
            "logging": {}
        }

        # Initialize built-in tools and resources
        self._register_builtin_tools()
        self._register_builtin_resources()
        self._register_builtin_prompts()

        # Request handlers
        self._handlers: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "ping": self._handle_ping,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "resources/subscribe": self._handle_resources_subscribe,
            "resources/unsubscribe": self._handle_resources_unsubscribe,
            "resources/templates/list": self._handle_resource_templates_list,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
            "logging/setLevel": self._handle_logging_set_level,
            "completion/complete": self._handle_completion,
        }

    def _register_builtin_tools(self):
        """Register built-in tools"""
        self._tools = {
            "get_current_time": {
                "name": "get_current_time",
                "description": "Returns the current server time in ISO 8601 format",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "Optional timezone (e.g., 'UTC', 'America/New_York')",
                            "default": "UTC"
                        }
                    },
                    "required": []
                }
            },
            "increment_counter": {
                "name": "increment_counter",
                "description": "Increments the server counter by a specified amount",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "integer",
                            "description": "Amount to increment by",
                            "default": 1
                        }
                    },
                    "required": []
                }
            },
            "add_note": {
                "name": "add_note",
                "description": "Adds a note to the server's note collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The note content"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for the note",
                            "default": []
                        }
                    },
                    "required": ["content"]
                }
            },
            "get_notes": {
                "name": "get_notes",
                "description": "Retrieves notes from the server, optionally filtered by tags",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of notes to return",
                            "default": 10
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter notes by these tags"
                        }
                    },
                    "required": []
                }
            },
            "calculate": {
                "name": "calculate",
                "description": "Performs basic arithmetic calculations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["add", "subtract", "multiply", "divide"],
                            "description": "The arithmetic operation"
                        },
                        "a": {
                            "type": "number",
                            "description": "First operand"
                        },
                        "b": {
                            "type": "number",
                            "description": "Second operand"
                        }
                    },
                    "required": ["operation", "a", "b"]
                }
            },
            "long_running_task": {
                "name": "long_running_task",
                "description": "Simulates a long-running task with progress updates",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "integer",
                            "description": "Number of steps to simulate",
                            "default": 5
                        },
                        "delay": {
                            "type": "number",
                            "description": "Delay between steps in seconds",
                            "default": 0.5
                        }
                    },
                    "required": []
                }
            }
        }

    def _register_builtin_resources(self):
        """Register built-in resources"""
        self._resources = {
            "server://status": {
                "uri": "server://status",
                "name": "Server Status",
                "description": "Current server status and health information",
                "mimeType": "application/json"
            },
            "server://notes": {
                "uri": "server://notes",
                "name": "All Notes",
                "description": "All notes stored on the server",
                "mimeType": "application/json"
            },
            "server://counter": {
                "uri": "server://counter",
                "name": "Counter Value",
                "description": "Current counter value",
                "mimeType": "text/plain"
            }
        }

        # Resource templates for dynamic resources
        self._resource_templates = [
            {
                "uriTemplate": "note://{id}",
                "name": "Individual Note",
                "description": "Access a specific note by ID",
                "mimeType": "application/json"
            }
        ]

    def _register_builtin_prompts(self):
        """Register built-in prompts"""
        self._prompts = {
            "greeting": {
                "name": "greeting",
                "description": "A customizable greeting message",
                "arguments": [
                    {
                        "name": "name",
                        "description": "Name of the person to greet",
                        "required": True
                    },
                    {
                        "name": "style",
                        "description": "Style of greeting (formal, casual, enthusiastic)",
                        "required": False
                    }
                ]
            },
            "summarize_notes": {
                "name": "summarize_notes",
                "description": "Creates a prompt to summarize stored notes",
                "arguments": [
                    {
                        "name": "max_notes",
                        "description": "Maximum number of notes to include",
                        "required": False
                    }
                ]
            }
        }

    # === Request Handlers ===

    async def _handle_initialize(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle initialize request"""
        session.client_info = params.get("clientInfo", {})
        session.client_capabilities = params.get("capabilities", {})

        logger.info(f"Client initialized: {session.client_info.get('name', 'unknown')}")

        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }

    async def _handle_initialized(
        self, params: Dict[str, Any], session: MCPSession
    ) -> None:
        """Handle initialized notification (no response needed)"""
        session.initialized = True
        logger.info(f"Session {session.session_id} fully initialized")
        return None  # Notifications don't return responses

    async def _handle_ping(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle ping request for health checks"""
        return {}

    async def _handle_tools_list(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle tools/list request"""
        cursor = params.get("cursor")
        # For simplicity, returning all tools (pagination can be added)
        return {
            "tools": list(self._tools.values())
        }

    async def _handle_tools_call(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle tools/call request - MCP spec compliant"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Execute tool
        result = await self._execute_tool(tool_name, arguments, session)
        return result

    async def _execute_tool(
        self, name: str, arguments: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Execute a tool and return result"""

        if name == "get_current_time":
            current_time = datetime.utcnow().isoformat() + "Z"
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Current time: {current_time}"
                    }
                ]
            }

        elif name == "increment_counter":
            amount = arguments.get("amount", 1)
            old_value = self.counter
            self.counter += amount

            # Notify subscribers about resource change
            await self._notify_resource_changed("server://counter", session)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Counter incremented from {old_value} to {self.counter}"
                    }
                ]
            }

        elif name == "add_note":
            content = arguments.get("content", "")
            tags = arguments.get("tags", [])

            note = {
                "id": len(self.notes) + 1,
                "content": content,
                "tags": tags,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            self.notes.append(note)

            # Notify subscribers about resource change
            await self._notify_resource_changed("server://notes", session)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Note added with ID: {note['id']}"
                    }
                ]
            }

        elif name == "get_notes":
            limit = arguments.get("limit", 10)
            filter_tags = arguments.get("tags", [])

            filtered = self.notes
            if filter_tags:
                filtered = [
                    n for n in self.notes
                    if any(t in n.get("tags", []) for t in filter_tags)
                ]

            result_notes = filtered[-limit:] if limit else filtered

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result_notes, indent=2)
                    }
                ]
            }

        elif name == "calculate":
            op = arguments.get("operation")
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)

            if op == "add":
                result = a + b
            elif op == "subtract":
                result = a - b
            elif op == "multiply":
                result = a * b
            elif op == "divide":
                if b == 0:
                    return {
                        "content": [{"type": "text", "text": "Error: Division by zero"}],
                        "isError": True
                    }
                result = a / b
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown operation: {op}"}],
                    "isError": True
                }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"{a} {op} {b} = {result}"
                    }
                ]
            }

        elif name == "long_running_task":
            steps = arguments.get("steps", 5)
            delay = arguments.get("delay", 0.5)

            # Send progress notifications via SSE
            for i in range(steps):
                await asyncio.sleep(delay)
                await self._send_progress(session, i + 1, steps, f"Step {i + 1} completed")

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Long-running task completed: {steps} steps"
                    }
                ]
            }

        else:
            return {
                "content": [{"type": "text", "text": f"Tool not implemented: {name}"}],
                "isError": True
            }

    async def _handle_resources_list(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle resources/list request"""
        return {
            "resources": list(self._resources.values())
        }

    async def _handle_resources_read(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri", "")

        if uri == "server://status":
            status = {
                "status": "healthy",
                "server": self.name,
                "version": self.version,
                "protocol_version": PROTOCOL_VERSION,
                "active_sessions": len(self.sessions),
                "notes_count": len(self.notes),
                "counter": self.counter,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(status, indent=2)
                    }
                ]
            }

        elif uri == "server://notes":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(self.notes, indent=2)
                    }
                ]
            }

        elif uri == "server://counter":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": str(self.counter)
                    }
                ]
            }

        elif uri.startswith("note://"):
            note_id = int(uri.replace("note://", ""))
            note = next((n for n in self.notes if n["id"] == note_id), None)
            if note:
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(note, indent=2)
                        }
                    ]
                }
            else:
                raise ValueError(f"Note not found: {note_id}")

        else:
            raise ValueError(f"Resource not found: {uri}")

    async def _handle_resources_subscribe(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle resources/subscribe request"""
        uri = params.get("uri", "")
        session.subscribed_resources.add(uri)
        logger.info(f"Session {session.session_id} subscribed to {uri}")
        return {}

    async def _handle_resources_unsubscribe(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle resources/unsubscribe request"""
        uri = params.get("uri", "")
        session.subscribed_resources.discard(uri)
        logger.info(f"Session {session.session_id} unsubscribed from {uri}")
        return {}

    async def _handle_resource_templates_list(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle resources/templates/list request"""
        return {
            "resourceTemplates": self._resource_templates
        }

    async def _handle_prompts_list(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle prompts/list request"""
        return {
            "prompts": list(self._prompts.values())
        }

    async def _handle_prompts_get(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle prompts/get request"""
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        if name == "greeting":
            person_name = arguments.get("name", "User")
            style = arguments.get("style", "casual")

            if style == "formal":
                text = f"Good day, {person_name}. How may I assist you today?"
            elif style == "enthusiastic":
                text = f"Hey {person_name}! Great to see you! What's up?"
            else:
                text = f"Hello, {person_name}! How can I help you?"

            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": text
                        }
                    }
                ]
            }

        elif name == "summarize_notes":
            max_notes = int(arguments.get("max_notes", 10))
            recent_notes = self.notes[-max_notes:]
            notes_text = "\n".join([
                f"- {n['content']} (tags: {', '.join(n.get('tags', []))})"
                for n in recent_notes
            ]) or "No notes available."

            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Please summarize these notes:\n\n{notes_text}"
                        }
                    }
                ]
            }

        else:
            raise ValueError(f"Prompt not found: {name}")

    async def _handle_logging_set_level(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle logging/setLevel request"""
        level = params.get("level", "info").upper()
        numeric_level = getattr(logging, level, logging.INFO)
        logger.setLevel(numeric_level)
        logger.info(f"Log level set to {level}")
        return {}

    async def _handle_completion(
        self, params: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Handle completion/complete request for argument auto-completion"""
        ref = params.get("ref", {})
        argument = params.get("argument", {})

        # Provide completions based on context
        completions = []

        ref_type = ref.get("type")
        if ref_type == "ref/prompt":
            prompt_name = ref.get("name")
            arg_name = argument.get("name")

            if prompt_name == "greeting" and arg_name == "style":
                completions = [
                    {"values": ["formal", "casual", "enthusiastic"]}
                ]

        return {
            "completion": {
                "values": completions[0]["values"] if completions else [],
                "hasMore": False
            }
        }

    # === Notification Helpers ===

    async def _send_progress(
        self, session: MCPSession, progress: int, total: int, message: str
    ):
        """Send progress notification via SSE"""
        if session.sse_queue:
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/progress",
                "params": {
                    "progress": progress,
                    "total": total,
                    "message": message
                }
            }
            await session.sse_queue.put(notification)

    async def _notify_resource_changed(self, uri: str, source_session: MCPSession):
        """Notify all subscribed sessions about resource changes"""
        for session in self.sessions.values():
            if uri in session.subscribed_resources and session.sse_queue:
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/resources/updated",
                    "params": {
                        "uri": uri
                    }
                }
                await session.sse_queue.put(notification)

    # === Main Request Processing ===

    async def handle_request(
        self, request: Dict[str, Any], session: MCPSession
    ) -> Optional[Dict[str, Any]]:
        """Process an incoming JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        logger.debug(f"Handling request: {method}")

        handler = self._handlers.get(method)
        if not handler:
            return self._error_response(
                request_id,
                ErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {method}"
            )

        try:
            result = await handler(params, session)

            # Notifications (like 'initialized') don't return responses
            if result is None and request_id is None:
                return None

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except ValueError as e:
            return self._error_response(request_id, ErrorCode.INVALID_PARAMS, str(e))
        except Exception as e:
            logger.exception(f"Error handling {method}")
            return self._error_response(request_id, ErrorCode.INTERNAL_ERROR, str(e))

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> Dict[str, Any]:
        """Create a JSON-RPC error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }


# === HTTP Transport Layer ===

class StreamableHTTPTransport:
    """
    Streamable HTTP Transport for MCP

    - POST /mcp: JSON-RPC requests
    - GET /mcp/sse: Server-Sent Events for notifications
    """

    def __init__(self, server: MCPServer, host: str = "0.0.0.0", port: int = 8000):
        self.server = server
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_post("/mcp", self._handle_post)
        self.app.router.add_get("/mcp/sse", self._handle_sse)
        self.app.router.add_get("/health", self._handle_health)

        # CORS middleware for browser clients
        self.app.middlewares.append(self._cors_middleware)

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler):
        """CORS middleware for cross-origin requests"""
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Session-ID"
        return response

    async def _get_or_create_session(self, request: web.Request) -> MCPSession:
        """Get existing session or create a new one"""
        session_id = request.headers.get("X-Session-ID")

        if session_id and session_id in self.server.sessions:
            return self.server.sessions[session_id]

        # Create new session
        session_id = str(uuid.uuid4())
        session = MCPSession(session_id=session_id)
        self.server.sessions[session_id] = session

        return session

    async def _handle_post(self, request: web.Request) -> web.Response:
        """Handle POST requests (JSON-RPC)"""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                self.server._error_response(None, ErrorCode.PARSE_ERROR, "Invalid JSON"),
                status=400
            )

        session = await self._get_or_create_session(request)

        # Handle batch requests
        if isinstance(body, list):
            responses = []
            for req in body:
                resp = await self.server.handle_request(req, session)
                if resp:
                    responses.append(resp)
            return web.json_response(responses, headers={"X-Session-ID": session.session_id})

        # Single request
        response = await self.server.handle_request(body, session)

        if response is None:
            # Notification - no content to return
            return web.Response(
                status=204,
                headers={"X-Session-ID": session.session_id}
            )

        return web.json_response(
            response,
            headers={"X-Session-ID": session.session_id}
        )

    async def _handle_sse(self, request: web.Request) -> web.StreamResponse:
        """Handle SSE connections for server-to-client notifications"""
        session = await self._get_or_create_session(request)

        # Create queue for this session's SSE events
        session.sse_queue = asyncio.Queue()

        logger.info(f"SSE connection established for session {session.session_id}")

        async with sse_response(request) as resp:
            # Send initial connection event
            await resp.send(json.dumps({
                "type": "connected",
                "sessionId": session.session_id
            }), event="connection")

            try:
                while True:
                    try:
                        # Wait for events with timeout to send keepalives
                        event = await asyncio.wait_for(
                            session.sse_queue.get(),
                            timeout=30.0
                        )
                        await resp.send(json.dumps(event), event="message")
                    except asyncio.TimeoutError:
                        # Send keepalive
                        await resp.send("", event="ping")
            except asyncio.CancelledError:
                logger.info(f"SSE connection closed for session {session.session_id}")
            finally:
                session.sse_queue = None

        return resp

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "server": self.server.name,
            "version": self.server.version,
            "protocol_version": PROTOCOL_VERSION
        })

    def run(self):
        """Start the HTTP server"""
        logger.info(f"Starting MCP server on http://{self.host}:{self.port}")
        logger.info(f"Protocol version: {PROTOCOL_VERSION}")
        logger.info("Endpoints:")
        logger.info(f"  POST /mcp     - JSON-RPC requests")
        logger.info(f"  GET  /mcp/sse - Server-Sent Events")
        logger.info(f"  GET  /health  - Health check")

        web.run_app(self.app, host=self.host, port=self.port, print=None)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server with Streamable HTTP")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--name", default="mcp-server", help="Server name")

    args = parser.parse_args()

    server = MCPServer(name=args.name)
    transport = StreamableHTTPTransport(server, host=args.host, port=args.port)
    transport.run()


if __name__ == "__main__":
    main()
