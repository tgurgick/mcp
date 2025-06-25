# Simple MCP Implementation

This directory contains a basic Model Context Protocol (MCP) implementation without AI integration, designed for learning and protocol demonstration.

## Files

- `simple_mcp_server.py` - Basic MCP server with in-memory resources and hardcoded tools
- `simple_test_client.py` - Test client for the simple server
- `simple_implementation.md` - Detailed documentation
- `README.md` - This file

## Quick Start

```bash
# Start the server
python simple_mcp_server.py

# In another terminal, start the client
python simple_test_client.py
```

## Features

- **No AI Integration**: Pure protocol implementation
- **In-Memory Resources**: Simple data storage
- **Hardcoded Tools**: Basic tool implementations
- **Protocol Demonstration**: Shows core MCP concepts

## Tools Available

- `get_current_time` - Get current server time
- `increment_counter` - Increment a counter
- `add_note` - Add notes to collection
- `get_notes` - Retrieve stored notes
- `calculate_sum` - Calculate sum of numbers

## Resources Available

- `current_time` - Current date and time
- `user_notes` - Collection of user notes
- `counter` - Simple counter value

## Purpose

This implementation serves as:
- Learning foundation for MCP concepts
- Protocol demonstration
- Testing framework
- Reference implementation

For more details, see [simple_implementation.md](simple_implementation.md). 