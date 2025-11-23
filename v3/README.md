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
| `mcp_server_observable.py` | Server with full observability |
| `README.md` | This documentation |

---

## Observability

The `mcp_server_observable.py` provides full production observability:

### Features

| Feature | Description |
|---------|-------------|
| **OpenTelemetry Tracing** | Distributed tracing with Jaeger/OTLP export |
| **Prometheus Metrics** | Request counts, latencies, errors, sessions |
| **Structured Logging** | JSON logs with trace correlation |
| **Request Validation** | Pydantic models for all requests |
| **Graceful Shutdown** | Proper cleanup on SIGTERM |
| **Health Endpoints** | `/health` and `/ready` for Kubernetes |

### Quick Start with Observability

```bash
# Basic usage (console tracing)
python mcp_server_observable.py --port 8000

# With OTLP exporter (for Jaeger)
OTEL_EXPORTER=otlp OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
  python mcp_server_observable.py

# Disable tracing
python mcp_server_observable.py --no-otel

# Full observability stack with Docker
docker-compose -f docker-compose.observability.yml up -d
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `0.0.0.0` | Server host |
| `MCP_PORT` | `8000` | Server port |
| `MCP_SERVER_NAME` | `mcp-server` | Server name for tracing |
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry |
| `OTEL_SERVICE_NAME` | `mcp-server` | Service name in traces |
| `OTEL_EXPORTER` | `console` | Exporter: `console`, `otlp` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP endpoint |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |
| `METRICS_PORT` | `9090` | Prometheus metrics port |
| `LOG_LEVEL` | `INFO` | Log level |
| `LOG_FORMAT` | `json` | Log format: `json`, `text` |

### Metrics Exposed

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mcp_requests_total` | Counter | `method` | Total requests |
| `mcp_request_duration_seconds` | Histogram | `method` | Request latency |
| `mcp_active_sessions` | Gauge | - | Active sessions |
| `mcp_tool_calls_total` | Counter | `tool` | Tool invocations |
| `mcp_errors_total` | Counter | `type` | Errors by type |

### Trace Context

Each trace includes:
- `mcp.method` - The JSON-RPC method
- `mcp.session_id` - Client session ID
- `mcp.protocol_version` - MCP protocol version
- Child spans for tool execution

### Structured Log Format

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "mcp",
  "message": "Client initializing",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "client_name": "my-client",
  "session_id": "sess-789"
}
```

### Docker Compose Stack

The `docker-compose.observability.yml` includes:

| Service | Port | Description |
|---------|------|-------------|
| `mcp-server` | 8000, 9090 | MCP server with metrics |
| `jaeger` | 16686, 4317 | Distributed tracing UI |
| `prometheus` | 9091 | Metrics collection |
| `grafana` | 3000 | Dashboards (admin/admin) |

```bash
# Start the stack
docker-compose -f docker-compose.observability.yml up -d

# Access services
open http://localhost:8000/health   # MCP Server
open http://localhost:16686         # Jaeger UI
open http://localhost:9091          # Prometheus
open http://localhost:3000          # Grafana
```

### Grafana Dashboard

A pre-configured dashboard shows:
- Total requests, sessions, errors, tool calls
- Request rate by method
- Request latency (p50, p95)
- Tool usage over time
- Error breakdown by type

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: mcp-server
        image: mcp-server:latest
        ports:
        - containerPort: 8000
        - containerPort: 9090
        env:
        - name: OTEL_EXPORTER
          value: "otlp"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://jaeger-collector:4317"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
```

### Integrating with Existing Observability

#### Datadog
```bash
OTEL_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://datadog-agent:4317 \
python mcp_server_observable.py
```

#### New Relic
```bash
pip install opentelemetry-exporter-otlp
OTEL_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.nr-data.net:4317 \
OTEL_EXPORTER_OTLP_HEADERS="api-key=YOUR_LICENSE_KEY" \
python mcp_server_observable.py
```

#### Grafana Cloud
```bash
OTEL_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp \
python mcp_server_observable.py
```
