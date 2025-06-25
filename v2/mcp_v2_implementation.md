# MCP v2 Implementation (2025-06-18 Specification)

This document describes the MCP v2 implementation that follows the latest Model Context Protocol specification (2025-06-18) with enhanced features including OAuth authorization, resource indicators, and improved security.

## Overview

The MCP v2 implementation represents a significant evolution from the previous version, incorporating:

- **OAuth 2.0 Authorization Support**: Full OAuth Resource Server implementation
- **Resource Indicators (RFC 8707)**: Enhanced security through resource validation
- **Structured Tool Output**: Rich, structured responses with metadata
- **Enhanced Security**: Improved authentication and authorization mechanisms
- **Protocol Version Headers**: Required version headers for compatibility
- **Elicitation Support**: Server-initiated information requests
- **Resource Links**: Links to related resources in tool responses

## Key Features

### 1. OAuth 2.0 Authorization

The v2 server implements OAuth 2.0 as a Resource Server:

```python
# OAuth metadata configuration
oauth_metadata = {
    "issuer": "https://mcp-v2-server.example.com",
    "authorization_endpoint": "https://auth.example.com/oauth/authorize",
    "token_endpoint": "https://auth.example.com/oauth/token",
    "resource_indicators": ["https://mcp-v2-server.example.com/api/*"],
    "scopes": ["read", "write", "admin"]
}
```

**Features:**
- Resource Server classification
- Protected resource metadata
- Scope-based access control
- Token validation and verification

### 2. Resource Indicators (RFC 8707)

Enhanced security through resource indicator validation:

```python
def _validate_resource_indicator(self, indicator: str) -> bool:
    """Validate resource indicator according to RFC 8707"""
    try:
        parsed = urlparse(indicator)
        return parsed.scheme in ["https", "http"] and parsed.netloc
    except:
        return False
```

**Benefits:**
- Prevents malicious servers from obtaining access tokens
- Validates resource URIs before authorization
- Ensures proper resource scope enforcement

### 3. Structured Tool Output

Tools now return rich, structured responses:

```python
{
    "content": "Tool result message",
    "structured": {
        "metadata": "Additional structured data",
        "format": "JSON schema"
    },
    "resource_links": [
        {
            "uri": "resource://link",
            "mimeType": "application/json",
            "title": "Related Resource"
        }
    ]
}
```

### 4. Enhanced Security

- **Protocol Version Headers**: Required `MCP-Protocol-Version` headers
- **Authentication Validation**: Per-tool authentication requirements
- **Rate Limiting**: Built-in rate limiting metadata
- **Input Validation**: Enhanced schema validation

### 5. New Protocol Methods

#### OAuth Methods

- `oauth/metadata`: Retrieve OAuth server metadata
- `oauth/authorize`: Request OAuth authorization

#### Enhanced Tool Methods

- `tools/call`: Enhanced with structured output and resource links
- `tools/list`: Enhanced metadata including authentication requirements

#### Enhanced Resource Methods

- `resources/read`: Enhanced with caching metadata
- `resources/list`: Enhanced resource metadata

## File Structure

```
mcp/
├── mcp_v2_server.py          # MCP v2 server implementation
├── mcp_v2_client.py          # MCP v2 client implementation
├── mcp_v2_implementation.md  # This documentation
├── env.example               # Environment variables template
└── requirements.txt          # Python dependencies
```

## Installation and Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` to include your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Running the Server

```bash
python mcp_v2_server.py
```

The server will start and listen for connections on the configured port.

### 4. Running the Client

#### Interactive Mode

```bash
python mcp_v2_client.py --mode interactive
```

#### Demo Mode

```bash
python mcp_v2_client.py --mode demo
```

#### With Authentication

```bash
python mcp_v2_client.py --auth --mode interactive
```

## Usage Examples

### 1. Basic Tool Usage

```python
# Initialize client
client = MCPv2Client("http://localhost:8000")

# List available tools
tools = client.list_tools()

# Call a tool
result = client.call_tool("get_current_time")
print(result["content"])
```

### 2. OAuth Authentication

```python
# Authenticate with OAuth
if client.authenticate(scope="read write"):
    print("Authentication successful!")
    
    # Now call protected tools
    result = client.call_tool("add_note", {
        "content": "Protected note",
        "tags": ["private"]
    })
```

### 3. Resource Access

```python
# List available resources
resources = client.list_resources()

# Read a resource
status = client.read_resource("server_status")
print(status["contents"][0]["text"])
```

### 4. Chat Completions

```python
# Send chat message
messages = [{"role": "user", "content": "What's the weather like?"}]
response = client.chat_completion(messages)

if "choices" in response:
    content = response["choices"][0]["message"]["content"]
    print(f"Assistant: {content}")
```

## Client Commands

In interactive mode, the client supports these commands:

- `/tools` - List available tools
- `/resources` - List available resources
- `/prompts` - List available prompts
- `/auth` - Authenticate with OAuth
- `/tool tool_name arg1=value1` - Call a specific tool
- `/resource uri` - Read a specific resource
- `/quit` - Exit the client

## Security Features

### 1. OAuth 2.0 Implementation

- **Resource Server**: Server acts as OAuth 2.0 Resource Server
- **Token Validation**: Validates Bearer tokens for protected resources
- **Scope Enforcement**: Enforces scope-based access control
- **Resource Indicators**: Validates resource URIs before authorization

### 2. Protocol Security

- **Version Headers**: Required protocol version headers
- **Input Validation**: Enhanced JSON schema validation
- **Error Handling**: Secure error responses without information leakage
- **Rate Limiting**: Built-in rate limiting for API protection

### 3. Authentication Flow

1. Client requests OAuth metadata
2. Client validates resource indicators
3. Client requests authorization with scopes
4. Server validates and issues access token
5. Client includes Bearer token in subsequent requests
6. Server validates token for protected operations

## Comparison with Previous Versions

| Feature | Simple | v1 (2024-11-05) | v2 (2025-06-18) |
|---------|--------|-----------------|-----------------|
| AI Integration | ❌ | ✅ | ✅ |
| OAuth Support | ❌ | ❌ | ✅ |
| Resource Indicators | ❌ | ❌ | ✅ |
| Structured Output | ❌ | ❌ | ✅ |
| Protocol Headers | ❌ | ❌ | ✅ |
| Enhanced Security | ❌ | ❌ | ✅ |
| Resource Links | ❌ | ❌ | ✅ |
| Elicitation | ❌ | ❌ | ✅ |

## API Reference

### Server Methods

#### Core Methods
- `initialize` - Initialize connection with protocol version
- `tools/list` - List available tools with metadata
- `tools/call` - Execute tools with structured output
- `resources/list` - List available resources
- `resources/read` - Read resources with caching
- `prompts/list` - List available prompts
- `prompts/get` - Get prompt content

#### OAuth Methods
- `oauth/metadata` - Get OAuth server metadata
- `oauth/authorize` - Request OAuth authorization

#### AI Methods
- `chat/completions` - AI-powered chat completions

### Client Methods

#### Connection
- `__init__(server_url)` - Initialize client connection
- `authenticate(scope, resource_indicators)` - OAuth authentication

#### Tools
- `list_tools()` - List available tools
- `call_tool(name, arguments)` - Execute tool with arguments

#### Resources
- `list_resources()` - List available resources
- `read_resource(uri)` - Read specific resource

#### Prompts
- `list_prompts()` - List available prompts
- `get_prompt(name, arguments)` - Get prompt content

#### AI
- `chat_completion(messages, model)` - Send chat completion request

#### Interactive
- `interactive_chat()` - Start interactive chat mode
- `demo_mode()` - Run demonstration mode

## Error Handling

The v2 implementation includes comprehensive error handling:

- **Protocol Errors**: Invalid JSON-RPC requests
- **Method Errors**: Unsupported methods
- **Parameter Errors**: Invalid parameters
- **Authentication Errors**: Missing or invalid authentication
- **Resource Errors**: Invalid resource URIs
- **Rate Limit Errors**: Exceeded rate limits

## Best Practices

### 1. Security
- Always validate resource indicators before authorization
- Use HTTPS in production environments
- Implement proper token storage and rotation
- Validate all input parameters

### 2. Performance
- Implement caching for frequently accessed resources
- Use appropriate rate limiting
- Monitor API usage and performance

### 3. Development
- Test with different OAuth scopes
- Validate structured output schemas
- Implement proper error handling
- Use protocol version headers

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check OAuth configuration
   - Verify resource indicators
   - Ensure proper token format

2. **Protocol Version Mismatch**
   - Update client/server to same version
   - Check protocol version headers

3. **Tool Execution Errors**
   - Verify tool parameters
   - Check authentication requirements
   - Review rate limiting

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Potential improvements for future versions:

1. **Advanced OAuth Flows**: PKCE, client credentials
2. **WebSocket Support**: Real-time communication
3. **Plugin Architecture**: Extensible tool system
4. **Advanced Caching**: Distributed caching
5. **Metrics and Monitoring**: Built-in observability

## Conclusion

The MCP v2 implementation provides a robust, secure, and feature-rich foundation for AI agent communication. With OAuth authorization, resource indicators, and structured output, it represents a significant advancement in the Model Context Protocol specification.

This implementation is production-ready and includes all the security and functionality improvements from the 2025-06-18 specification. 