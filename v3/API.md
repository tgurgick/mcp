# MCP Server API Reference

Complete API reference for the MCP v3 implementation.

## Transport

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp` | POST | JSON-RPC 2.0 endpoint for all MCP requests |
| `/mcp/sse` | GET | Server-Sent Events for notifications |
| `/health` | GET | Health check endpoint |

### Headers

| Header | Type | Description |
|--------|------|-------------|
| `Content-Type` | Request | Must be `application/json` |
| `X-Session-ID` | Request/Response | Session identifier for state persistence |
| `Accept` | Request | Use `text/event-stream` for SSE |

---

## JSON-RPC Format

### Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "method/name",
  "params": {}
}
```

### Response (Success)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { ... }
}
```

### Response (Error)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Error description",
    "data": { ... }
  }
}
```

### Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Not a valid JSON-RPC request |
| -32601 | Method not found | Method doesn't exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Server error |

---

## Protocol Methods

### initialize

Initialize the MCP connection. Must be called first.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "clientInfo": {
      "name": "my-client",
      "version": "1.0.0"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true, "listChanged": true },
      "prompts": { "listChanged": true }
    },
    "serverInfo": {
      "name": "mcp-server",
      "version": "1.0.0"
    }
  }
}
```

---

### initialized (Notification)

Notify server that client is ready. No response.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "initialized",
  "params": {}
}
```

---

### ping

Health check for the connection.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "ping",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {}
}
```

---

## Tools

### tools/list

List all available tools.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "tools": [
      {
        "name": "get_current_time",
        "description": "Get the current time",
        "inputSchema": {
          "type": "object",
          "properties": {},
          "required": []
        }
      },
      {
        "name": "calculate",
        "description": "Perform arithmetic operations",
        "inputSchema": {
          "type": "object",
          "properties": {
            "operation": {
              "type": "string",
              "enum": ["add", "subtract", "multiply", "divide"]
            },
            "a": { "type": "number" },
            "b": { "type": "number" }
          },
          "required": ["operation", "a", "b"]
        }
      }
    ]
  }
}
```

---

### tools/call

Execute a tool.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "calculate",
    "arguments": {
      "operation": "add",
      "a": 5,
      "b": 3
    }
  }
}
```

**Response (Success):**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "5 + 3 = 8"
      }
    ]
  }
}
```

**Response (Error):**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Error: Division by zero"
      }
    ],
    "isError": true
  }
}
```

---

## Resources

### resources/list

List all available resources.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "resources/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "resources": [
      {
        "uri": "server://status",
        "name": "Server Status",
        "description": "Current server status",
        "mimeType": "application/json"
      },
      {
        "uri": "server://counter",
        "name": "Counter",
        "description": "Current counter value",
        "mimeType": "text/plain"
      }
    ]
  }
}
```

---

### resources/read

Read a resource by URI.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "resources/read",
  "params": {
    "uri": "server://status"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "contents": [
      {
        "uri": "server://status",
        "mimeType": "application/json",
        "text": "{\"status\": \"healthy\", \"uptime\": 3600}"
      }
    ]
  }
}
```

---

### resources/subscribe

Subscribe to resource change notifications.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "resources/subscribe",
  "params": {
    "uri": "server://counter"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {}
}
```

---

### resources/unsubscribe

Unsubscribe from resource notifications.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "resources/unsubscribe",
  "params": {
    "uri": "server://counter"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "result": {}
}
```

---

## Prompts

### prompts/list

List available prompt templates.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "method": "prompts/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "result": {
    "prompts": [
      {
        "name": "greeting",
        "description": "Generate a personalized greeting",
        "arguments": [
          {
            "name": "name",
            "description": "Name of the person to greet",
            "required": true
          },
          {
            "name": "style",
            "description": "Greeting style (formal/casual)",
            "required": false
          }
        ]
      }
    ]
  }
}
```

---

### prompts/get

Get a prompt with arguments filled in.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "prompts/get",
  "params": {
    "name": "greeting",
    "arguments": {
      "name": "Alice",
      "style": "formal"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Please greet Alice in a formal style."
        }
      }
    ]
  }
}
```

---

## Server-Sent Events (SSE)

Connect to `/mcp/sse` with `Accept: text/event-stream` header.

### Event Types

#### connection

Initial connection confirmation.

```
event: connection
data: {"type": "connected", "session_id": "abc123"}
```

#### notification

Server notifications (resource changes, progress updates).

```
event: notification
data: {"jsonrpc": "2.0", "method": "notifications/resources/updated", "params": {"uri": "server://counter"}}
```

#### progress

Progress updates for long-running operations.

```
event: progress
data: {"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progressToken": "task-1", "progress": 50, "total": 100}}
```

---

## Built-in Tools

### get_current_time

Get the current server time.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (none) | | | |

### calculate

Perform arithmetic operations.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | One of: add, subtract, multiply, divide |
| a | number | Yes | First operand |
| b | number | Yes | Second operand |

### increment_counter

Increment the server counter.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| amount | integer | No | Amount to increment (default: 1) |

### add_note

Add a note to the server.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| content | string | Yes | Note content |
| tags | array | No | Tags for the note |

### get_notes

Retrieve stored notes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| tags | array | No | Filter by tags |
| limit | integer | No | Maximum notes to return |

### long_running_task

Demo tool that shows progress notifications.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| steps | integer | No | Number of steps (default: 5) |
| delay | number | No | Delay per step in seconds |

---

## Python Client Usage

```python
import asyncio
from mcp_client import MCPClient

async def main():
    client = MCPClient("http://localhost:8000")

    # Connect and initialize
    await client.connect()

    # List tools
    tools = await client.list_tools()
    print(f"Available tools: {[t['name'] for t in tools]}")

    # Call a tool
    result = await client.call_tool("calculate", {
        "operation": "multiply",
        "a": 6,
        "b": 7
    })
    print(f"Result: {result}")

    # Read a resource
    status = await client.read_resource("server://status")
    print(f"Status: {status}")

    # Close connection
    await client.close()

asyncio.run(main())
```

---

## cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Initialize
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'

# List tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: your-session-id" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Call tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: your-session-id" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_current_time","arguments":{}}}'

# SSE connection
curl -N -H "Accept: text/event-stream" http://localhost:8000/mcp/sse
```

---

## Error Handling

### Common Errors

| Error | Code | Cause | Solution |
|-------|------|-------|----------|
| Method not found | -32601 | Unknown method | Check method name spelling |
| Invalid params | -32602 | Missing/wrong params | Check parameter requirements |
| Unknown tool | -32602 | Tool doesn't exist | Use tools/list to see available tools |
| Resource not found | -32602 | URI not found | Use resources/list to see available URIs |

### Best Practices

1. Always call `initialize` first
2. Store and reuse `X-Session-ID` for state persistence
3. Handle errors gracefully with retry logic
4. Use SSE for real-time notifications
5. Validate tool arguments before calling
