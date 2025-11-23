# Model Context Protocol (MCP) Implementations

This repository contains multiple implementations of the Model Context Protocol, demonstrating the evolution from basic concepts to production-ready implementations.

## Recommended: v3 Implementation

**For production use, start with `v3/`** - it provides a fully compliant MCP implementation with proper Streamable HTTP transport.

```bash
# Quick start with v3
pip install -r requirements.txt
cd v3
python mcp_server.py --port 8000

# In another terminal
python mcp_client.py --mode demo
```

## Implementations Overview

| Version | Specification | Transport | Production Ready |
|---------|--------------|-----------|------------------|
| **v3** (Recommended) | 2024-11-05 | Streamable HTTP + SSE | Yes |
| v2 | Custom | HTTP (mock) | No |
| v1 | 2024-11-05 | Stdio | Educational |
| simple | Basic | Stdio | Educational |

### v3 - Production Ready (`v3/`)
- **Specification**: Official 2024-11-05
- **Transport**: Streamable HTTP (POST + SSE) and Stdio
- **Features**:
  - Real HTTP server with `aiohttp`
  - Server-Sent Events for notifications
  - Progress updates for long-running operations
  - Resource subscriptions
  - Multi-client session management
- **Documentation**: [v3 README](v3/README.md)

### v2 - Educational (`v2/`)
- **Specification**: Custom (fictional 2025-06-18)
- **Status**: Educational only - has architectural issues
- **Issues**:
  - No actual HTTP server (REPL-based)
  - Mock OAuth implementation
  - Non-standard tools/call schema
- **Documentation**: [v2 Implementation Guide](v2/mcp_v2_implementation.md)

### v1 - Educational (`v1/`)
- **Specification**: 2024-11-05
- **Features**: OpenAI integration, conversation history
- **Transport**: Stdio only
- **Documentation**: [v1 Implementation Guide](v1/mcp_v1_implementation.md)

### Simple - Learning (`simple/`)
- **Purpose**: Basic protocol demonstration
- **Features**: In-memory resources, hardcoded tools, no AI
- **Documentation**: [Simple Implementation Guide](simple/simple_implementation.md)

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Running v3 (Recommended)

```bash
# HTTP Server
cd v3
python mcp_server.py --port 8000

# In another terminal - Interactive client
python mcp_client.py --server http://localhost:8000

# Or run demo
python mcp_client.py --mode demo
```

### Stdio Mode (for subprocess usage)

```bash
cd v3
python mcp_stdio_server.py
```

## Feature Comparison

| Feature | simple | v1 | v2 | v3 |
|---------|--------|----|----|-----|
| **Real HTTP Server** | - | - | No | Yes |
| **SSE Streaming** | - | - | No | Yes |
| **Progress Notifications** | - | - | No | Yes |
| **Resource Subscriptions** | - | - | No | Yes |
| **Session Management** | - | - | No | Yes |
| **Stdio Transport** | Yes | Yes | No | Yes |
| **Protocol Compliant** | Partial | Yes | No | Yes |
| **AI Integration** | No | Yes | Yes | Optional |

## Protocol Methods (v3)

| Category | Method | Description |
|----------|--------|-------------|
| Lifecycle | `initialize` | Initialize connection |
| | `initialized` | Confirm initialization |
| | `ping` | Health check |
| Tools | `tools/list` | List available tools |
| | `tools/call` | Execute a tool |
| Resources | `resources/list` | List resources |
| | `resources/read` | Read a resource |
| | `resources/subscribe` | Subscribe to changes |
| | `resources/unsubscribe` | Unsubscribe |
| | `resources/templates/list` | List URI templates |
| Prompts | `prompts/list` | List prompts |
| | `prompts/get` | Get prompt content |
| Utilities | `logging/setLevel` | Set log level |
| | `completion/complete` | Argument completion |

## Directory Structure

```
mcp/
├── v3/                              # Production-ready (RECOMMENDED)
│   ├── mcp_server.py                # HTTP server with SSE
│   ├── mcp_client.py                # Async client
│   ├── mcp_stdio_server.py          # Stdio transport
│   └── README.md
├── v2/                              # Educational (has issues)
│   ├── mcp_v2_server.py
│   ├── mcp_v2_client.py
│   └── mcp_v2_implementation.md
├── v1/                              # Educational (stdio only)
│   ├── mcp_v1_server.py
│   ├── mcp_v1_client.py
│   └── mcp_v1_implementation.md
├── simple/                          # Basic learning
│   ├── simple_mcp_server.py
│   ├── simple_test_client.py
│   └── simple_implementation.md
├── requirements.txt                 # Python dependencies
├── env.example                      # Environment template
└── README.md                        # This file
```

## Client Commands (v3)

```
/tools              - List available tools
/call <name> [json] - Call a tool
/resources          - List resources
/read <uri>         - Read a resource
/subscribe <uri>    - Subscribe to resource
/prompts            - List prompts
/prompt <name> [json] - Get a prompt
/ping               - Ping server
/status             - Read server status
/help               - Show help
/quit               - Exit
```

## Environment Setup

For AI features in v1/v2:

```bash
cp env.example .env
# Edit .env to add your OpenAI API key
```

## Troubleshooting

### v3 Connection Issues
```bash
# Check server is running
curl http://localhost:8000/health

# Check SSE endpoint
curl http://localhost:8000/mcp/sse
```

### Dependency Issues
```bash
pip install --upgrade aiohttp aiohttp-sse aiohttp-sse-client
```

### OpenAI API Key (v1/v2)
- Ensure `.env` file contains `OPENAI_API_KEY`
- Required only for AI-powered features

## Migration from v2 to v3

Key changes:
1. **Transport**: v3 uses real HTTP server, v2 was REPL-based
2. **tools/call**: v3 uses `{name, arguments}`, v2 used `{calls: [...]}`
3. **Protocol version**: v3 uses official `2024-11-05`
4. **Notifications**: v3 implements SSE-based notifications

## License

MIT License
