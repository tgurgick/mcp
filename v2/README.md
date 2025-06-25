# MCP v2 Implementation (2025-06-18 Specification)

This directory contains the latest MCP v2 implementation with OAuth authorization, resource indicators, and enhanced security, following the 2025-06-18 specification.

## Files

- `mcp_v2_server.py` - Latest MCP server with OAuth and enhanced security
- `mcp_v2_client.py` - Client for the v2 server with OAuth support
- `mcp_v2_implementation.md` - Detailed documentation
- `README.md` - This file

## Quick Start

### Prerequisites

1. Install dependencies from the root directory:
```bash
cd ..  # Go back to root
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp ../env.example ../.env
# Edit ../.env and add your OpenAI API key
```

### Running

```bash
# Start the server
python mcp_v2_server.py

# In another terminal, start the client with authentication
python mcp_v2_client.py --auth --mode interactive
```

## Features

- **OAuth 2.0 Authorization**: Full OAuth Resource Server implementation
- **Resource Indicators (RFC 8707)**: Enhanced security through resource validation
- **Structured Tool Output**: Rich, structured responses with metadata
- **Enhanced Security**: Protocol version headers, rate limiting, input validation
- **Resource Links**: Links to related resources in tool responses
- **AI Integration**: OpenAI GPT-4 powered responses
- **Elicitation Support**: Server-initiated information requests

## Tools Available

- `get_current_time` - Get current server time
- `increment_counter` - Increment a counter (requires auth)
- `add_note` - Add notes to collection (requires auth)
- `get_notes` - Retrieve stored notes (requires auth)
- `calculate_sum` - Calculate sum of numbers
- `get_weather_info` - Get weather information (requires auth)

## Client Commands

In interactive mode:
- `/tools` - List available tools
- `/resources` - List available resources
- `/prompts` - List available prompts
- `/auth` - Authenticate with OAuth
- `/tool tool_name arg1=value1` - Call a specific tool
- `/resource uri` - Read a specific resource
- `/quit` - Exit the client

## Demo Mode

```bash
python mcp_v2_client.py --mode demo
```

## OAuth Authentication

The v2 implementation supports OAuth 2.0 authorization:

```bash
# Authenticate on startup
python mcp_v2_client.py --auth --mode interactive

# Or authenticate during session
/auth
```

### Authentication Flow

1. Client requests OAuth metadata
2. Client validates resource indicators
3. Client requests authorization with scopes
4. Server validates and issues access token
5. Client includes Bearer token in subsequent requests
6. Server validates token for protected operations

## Security Features

- **Resource Server**: OAuth 2.0 Resource Server implementation
- **Token Validation**: Validates Bearer tokens for protected resources
- **Scope Enforcement**: Enforces scope-based access control
- **Resource Indicators**: Validates resource URIs before authorization
- **Protocol Headers**: Required `MCP-Protocol-Version` headers
- **Rate Limiting**: Built-in rate limiting for API protection

## Purpose

This implementation provides:
- Latest MCP specification compliance
- Production-ready security features
- OAuth 2.0 authorization
- Enhanced tool and resource capabilities
- Structured output and metadata

For more details, see [mcp_v2_implementation.md](mcp_v2_implementation.md). 