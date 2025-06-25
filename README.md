# Model Context Protocol (MCP) Implementations

This repository contains three independent implementations of the Model Context Protocol, each demonstrating different aspects and versions of the specification.

## Implementations Overview

### 1. Simple MCP Implementation (`simple/`)
- **Specification**: Basic MCP concepts
- **Features**: In-memory resources, hardcoded tools, no AI integration
- **Purpose**: Protocol demonstration and learning foundation
- **Documentation**: [Simple Implementation Guide](simple/simple_implementation.md)

### 2. MCP v1 Implementation (`v1/`) 
- **Specification**: 2024-11-05
- **Features**: OpenAI integration, conversation history, AI-driven tool selection
- **Purpose**: Production-ready AI-powered MCP server
- **Documentation**: [MCP v1 Implementation Guide](v1/mcp_v1_implementation.md)

### 3. MCP v2 Implementation (`v2/`)
- **Specification**: 2025-06-18 (Latest)
- **Features**: OAuth 2.0 authorization, resource indicators (RFC 8707), structured output, enhanced security
- **Purpose**: Latest specification with advanced security and features
- **Documentation**: [MCP v2 Implementation Guide](v2/mcp_v2_implementation.md)

## Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

### Environment Setup
```bash
cp env.example .env
# Edit .env to add your OpenAI API key for v1 and v2 servers
```

### Running Different Implementations

#### Simple Implementation (No AI)
```bash
# Terminal 1: Start server
cd simple
python simple_mcp_server.py

# Terminal 2: Start client
cd simple
python simple_test_client.py
```

#### MCP v1 Implementation (AI-Powered)
```bash
# Terminal 1: Start server
cd v1
python mcp_v1_server.py

# Terminal 2: Start client
cd v1
python mcp_v1_client.py --mode interactive
```

#### MCP v2 Implementation (Latest Spec with Auth)
```bash
# Terminal 1: Start server
cd v2
python mcp_v2_server.py

# Terminal 2: Start client with authentication
cd v2
python mcp_v2_client.py --auth --mode interactive
```

## Feature Comparison

| Feature | Simple | v1 (2024-11-05) | v2 (2025-06-18) |
|---------|--------|-----------------|-----------------|
| **AI Integration** | ❌ | ✅ | ✅ |
| **OAuth Support** | ❌ | ❌ | ✅ |
| **Resource Indicators** | ❌ | ❌ | ✅ |
| **Structured Output** | ❌ | ❌ | ✅ |
| **Protocol Headers** | ❌ | ❌ | ✅ |
| **Enhanced Security** | ❌ | ❌ | ✅ |
| **Resource Links** | ❌ | ❌ | ✅ |
| **Elicitation** | ❌ | ❌ | ✅ |
| **Rate Limiting** | ❌ | ❌ | ✅ |
| **Caching** | ❌ | ❌ | ✅ |

## Directory Structure

```
mcp/
├── simple/                          # Simple implementation (no AI)
│   ├── simple_mcp_server.py
│   ├── simple_test_client.py
│   ├── simple_implementation.md
│   └── README.md
├── v1/                              # MCP v1 implementation (2024-11-05 spec)
│   ├── mcp_v1_server.py
│   ├── mcp_v1_client.py
│   ├── mcp_v1_implementation.md
│   └── README.md
├── v2/                              # MCP v2 implementation (2025-06-18 spec)
│   ├── mcp_v2_server.py
│   ├── mcp_v2_client.py
│   ├── mcp_v2_implementation.md
│   └── README.md
├── env.example                      # Environment variables template
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Client Commands

### Interactive Mode Commands (v1 & v2)
- `/tools` - List available tools
- `/resources` - List available resources  
- `/prompts` - List available prompts
- `/auth` - Authenticate with OAuth (v2 only)
- `/tool tool_name arg1=value1` - Call a specific tool
- `/resource uri` - Read a specific resource
- `/quit` - Exit the client

### Demo Mode
```bash
# v1 demo
cd v1
python mcp_v1_client.py --mode demo

# v2 demo
cd v2
python mcp_v2_client.py --mode demo
```

## Security Features (v2)

### OAuth 2.0 Authorization
- Resource Server implementation
- Scope-based access control
- Token validation and verification
- Resource indicator validation (RFC 8707)

### Enhanced Security
- Protocol version headers
- Input validation
- Rate limiting
- Secure error handling

## Development

### Testing Different Implementations

1. **Simple**: Test basic MCP concepts without AI
   ```bash
   cd simple
   python simple_mcp_server.py
   ```

2. **v1**: Test AI-powered features with OpenAI
   ```bash
   cd v1
   python mcp_v1_server.py
   ```

3. **v2**: Test latest specification with OAuth and enhanced security
   ```bash
   cd v2
   python mcp_v2_server.py
   ```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Troubleshooting

### Common Issues

1. **OpenAI API Key Missing**
   - Ensure `.env` file contains `OPENAI_API_KEY`
   - Required for v1 and v2 implementations

2. **Authentication Failures (v2)**
   - Check OAuth configuration
   - Verify resource indicators
   - Ensure proper token format

3. **Protocol Version Mismatch**
   - Use matching client/server versions
   - Check protocol version headers

### Getting Help

- Check the specific implementation documentation in each directory
- Review error messages in the console
- Enable debug logging for detailed information

## Contributing

Each implementation is designed to be independent and self-contained. When contributing:

1. Choose the appropriate implementation directory to modify
2. Follow the existing code style and patterns
3. Update the corresponding documentation
4. Test with the matching client

## License

This project is open source and available under the MIT License. 