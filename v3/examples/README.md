# MCP Examples

Real-world examples of using and extending MCP servers.

## Quick Start Examples

| Example | Description | File |
|---------|-------------|------|
| **File Browser** | Browse and read files | `file_browser_tool.py` |
| **Database Query** | Query SQLite databases | `database_tool.py` |
| **Web Scraper** | Fetch and parse web pages | `web_scraper_tool.py` |
| **Claude Integration** | Use MCP with Claude API | `claude_integration.py` |

## Running Examples

```bash
# Start the example server
python example_server.py

# In another terminal, run the client
python ../mcp_client.py --mode demo
```

## Using with AI Frameworks

### Claude API

See `claude_integration.py` for a complete example of:
- Connecting to MCP server
- Getting available tools
- Converting tools to Claude format
- Handling tool calls in conversation

### LangChain

See `langchain_integration.py` for:
- Creating LangChain tools from MCP
- Using in agent workflows
- Streaming responses

## Creating Custom Tools

1. Copy a tool template from this directory
2. Modify the tool definition and execution logic
3. Register in your server
4. Test with diagnostics: `python ../mcp_cli.py test`
