# MCP v3 - Production-Ready Implementation

This directory contains a **production-ready** Model Context Protocol implementation following the official **2024-11-05 specification**.

## Key Features

| Feature | Status | Description |
|---------|--------|-------------|
| **Streamable HTTP Transport** | Complete | POST for requests, SSE for streaming |
| **Stdio Transport** | Complete | For local subprocess communication |
| **Protocol Compliance** | Complete | Official 2024-11-05 specification |
| **Tools** | Complete | With progress notifications |
| **Resources** | Complete | With subscriptions and templates |
| **Prompts** | Complete | With argument completion |
| **Session Management** | Complete | Multi-client support |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Server                             │
├─────────────────────────────────────────────────────────────┤
│  Transport Layer                                            │
│  ├── StreamableHTTPTransport (aiohttp + SSE)                │
│  └── StdioTransport (stdin/stdout JSON-RPC)                 │
├─────────────────────────────────────────────────────────────┤
│  Protocol Layer (JSON-RPC 2.0)                              │
│  ├── Request/Response Handler                               │
│  ├── Notification Handler                                   │
│  └── Session Management                                     │
├─────────────────────────────────────────────────────────────┤
│  Feature Layer                                              │
│  ├── Tools (with progress support)                          │
│  ├── Resources (with subscriptions & templates)             │
│  ├── Prompts (with completion)                              │
│  └── Logging                                                │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r ../requirements.txt
```

### 2. Start the HTTP Server

```bash
python mcp_server.py --port 8000
```

### 3. Connect with Client

```bash
# Interactive mode
python mcp_client.py --server http://localhost:8000

# Demo mode
python mcp_client.py --server http://localhost:8000 --mode demo
```

## Transport Options

### Streamable HTTP (Recommended for Remote)

```bash
# Server
python mcp_server.py --host 0.0.0.0 --port 8000

# Endpoints:
#   POST /mcp      - JSON-RPC requests
#   GET  /mcp/sse  - Server-Sent Events for notifications
#   GET  /health   - Health check
```

### Stdio (For Local Subprocess)

```bash
# Run as subprocess
python mcp_stdio_server.py

# Send requests via stdin, receive via stdout
echo '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}' | python mcp_stdio_server.py
```

## Protocol Compliance

### Supported Methods

| Category | Method | Description |
|----------|--------|-------------|
| **Lifecycle** | `initialize` | Initialize connection |
| | `initialized` | Confirm initialization (notification) |
| | `ping` | Health check |
| **Tools** | `tools/list` | List available tools |
| | `tools/call` | Execute a tool |
| **Resources** | `resources/list` | List resources |
| | `resources/read` | Read a resource |
| | `resources/subscribe` | Subscribe to changes |
| | `resources/unsubscribe` | Unsubscribe |
| | `resources/templates/list` | List URI templates |
| **Prompts** | `prompts/list` | List prompts |
| | `prompts/get` | Get prompt content |
| **Utilities** | `logging/setLevel` | Set log level |
| | `completion/complete` | Argument completion |

### Notifications (Server → Client)

| Notification | Description |
|--------------|-------------|
| `notifications/progress` | Progress updates for long-running operations |
| `notifications/resources/updated` | Resource change notifications |

## Built-in Tools

| Tool | Description | Arguments |
|------|-------------|-----------|
| `get_current_time` | Get server time | `timezone` (optional) |
| `increment_counter` | Increment counter | `amount` (default: 1) |
| `add_note` | Add a note | `content`, `tags` |
| `get_notes` | Retrieve notes | `limit`, `tags` |
| `calculate` | Arithmetic operations | `operation`, `a`, `b` |
| `long_running_task` | Demo with progress | `steps`, `delay` |

## Built-in Resources

| URI | Description | Type |
|-----|-------------|------|
| `server://status` | Server health info | application/json |
| `server://notes` | All stored notes | application/json |
| `server://counter` | Counter value | text/plain |
| `note://{id}` | Individual note | application/json |

## Usage Examples

### Python Client

```python
import asyncio
from mcp_client import MCPClient

async def main():
    async with MCPClient("http://localhost:8000") as client:
        # List tools
        tools = await client.list_tools()
        print(f"Available tools: {[t['name'] for t in tools]}")

        # Call a tool
        result = await client.call_tool("calculate", {
            "operation": "multiply",
            "a": 7,
            "b": 8
        })
        print(result["content"][0]["text"])

        # Subscribe to resource updates
        await client.subscribe_resource("server://counter")

        # Read a resource
        status = await client.read_resource("server://status")
        print(status["contents"][0]["text"])

asyncio.run(main())
```

### Direct HTTP Requests

```bash
# Initialize
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "curl", "version": "1.0"}
    }
  }'

# Call a tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: <session-id-from-init>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "get_current_time",
      "arguments": {}
    }
  }'
```

## Differences from v1/v2

| Aspect | v1/v2 | v3 |
|--------|-------|-----|
| **Transport** | Fake HTTP (REPL) | Real HTTP server with SSE |
| **Protocol Version** | "2025-06-18" (fictional) | "2024-11-05" (official) |
| **tools/call Schema** | Custom `calls` array | Standard `name` + `arguments` |
| **Notifications** | None | SSE-based progress & updates |
| **Session Management** | None | Full multi-client support |
| **Resource Subscriptions** | Mentioned but not implemented | Fully implemented |
| **OAuth** | Simulated | Removed (implement separately) |

## Extending the Server

### Adding a New Tool

```python
# In MCPServer._register_builtin_tools():
self._tools["my_tool"] = {
    "name": "my_tool",
    "description": "Does something useful",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
}

# In MCPServer._execute_tool():
elif name == "my_tool":
    param1 = arguments.get("param1")
    # ... do something
    return {
        "content": [{"type": "text", "text": f"Result: {result}"}]
    }
```

### Adding a New Resource

```python
# In MCPServer._register_builtin_resources():
self._resources["myapp://data"] = {
    "uri": "myapp://data",
    "name": "My Data",
    "description": "Custom data resource",
    "mimeType": "application/json"
}

# In MCPServer._handle_resources_read():
elif uri == "myapp://data":
    return {
        "contents": [{
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(my_data)
        }]
    }
```

## Testing

```bash
# Start server in one terminal
python mcp_server.py

# Run demo in another terminal
python mcp_client.py --mode demo

# Or run interactive client
python mcp_client.py
```

## Files

| File | Description |
|------|-------------|
| `mcp_server.py` | Main server with HTTP transport |
| `mcp_client.py` | Async client with SSE support |
| `mcp_stdio_server.py` | Stdio transport variant |
| `README.md` | This documentation |
