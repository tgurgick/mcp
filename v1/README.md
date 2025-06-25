# MCP v1 Implementation (2024-11-05 Specification)

This directory contains the MCP v1 implementation with AI integration using OpenAI, following the 2024-11-05 specification.

## Files

- `mcp_v1_server.py` - AI-powered MCP server with OpenAI integration
- `mcp_v1_client.py` - Client for the v1 server with interactive chat
- `mcp_v1_implementation.md` - Detailed documentation
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
python mcp_v1_server.py

# In another terminal, start the client
python mcp_v1_client.py --mode interactive
```

## Features

- **AI Integration**: OpenAI GPT-4 powered responses
- **Natural Language**: Conversational interface
- **Tool Selection**: AI-driven tool selection
- **Context Memory**: Session history maintained
- **Conversation Flow**: Natural language processing

## Tools Available

- `get_current_time` - Get current server time
- `increment_counter` - Increment a counter
- `add_note` - Add notes to collection
- `get_notes` - Retrieve stored notes
- `calculate_sum` - Calculate sum of numbers
- `get_weather_info` - Get weather information (simulated)

## Client Commands

In interactive mode:
- `/tools` - List available tools
- `/resources` - List available resources
- `/prompts` - List available prompts
- `/tool tool_name arg1=value1` - Call a specific tool
- `/resource uri` - Read a specific resource
- `/quit` - Exit the client

## Demo Mode

```bash
python mcp_v1_client.py --mode demo
```

## Purpose

This implementation provides:
- Production-ready AI-powered MCP server
- Natural language interaction
- OpenAI integration
- Conversation management

For more details, see [mcp_v1_implementation.md](mcp_v1_implementation.md). 