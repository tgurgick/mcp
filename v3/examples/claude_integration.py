#!/usr/bin/env python3
"""
Claude API + MCP Integration Example

This example shows how to:
1. Connect to an MCP server
2. Get available tools and convert them to Claude format
3. Use tools in a conversation with Claude
4. Handle tool results and continue the conversation

Requirements:
    pip install anthropic aiohttp

Usage:
    # Start MCP server first
    python ../mcp_server.py

    # Then run this example
    export ANTHROPIC_API_KEY=your_key
    python claude_integration.py
"""

import asyncio
import json
import os
from typing import Any, Dict, List

# Check for required packages
try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    exit(1)

try:
    import aiohttp
except ImportError:
    print("Please install aiohttp: pip install aiohttp")
    exit(1)


class MCPClaudeAdapter:
    """
    Adapter that connects MCP servers to Claude API.

    Handles:
    - Tool discovery from MCP server
    - Converting MCP tools to Claude tool format
    - Executing tool calls via MCP
    - Managing conversation flow
    """

    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        self.mcp_url = mcp_server_url.rstrip("/")
        self.session_id: str | None = None
        self.claude = anthropic.Anthropic()
        self.mcp_tools: List[Dict] = []
        self.claude_tools: List[Dict] = []

    async def connect(self):
        """Initialize connection to MCP server"""
        async with aiohttp.ClientSession() as session:
            # Initialize MCP connection
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "claude-adapter", "version": "1.0.0"}
                }
            }

            async with session.post(
                f"{self.mcp_url}/mcp",
                json=init_request
            ) as resp:
                self.session_id = resp.headers.get("X-Session-ID")
                data = await resp.json()

                if "error" in data:
                    raise RuntimeError(f"MCP init failed: {data['error']}")

                print(f"Connected to MCP server: {data['result']['serverInfo']['name']}")

            # Get available tools
            await self._load_tools(session)

    async def _load_tools(self, session: aiohttp.ClientSession):
        """Load tools from MCP server and convert to Claude format"""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        async with session.post(
            f"{self.mcp_url}/mcp",
            json=request,
            headers={"X-Session-ID": self.session_id}
        ) as resp:
            data = await resp.json()
            self.mcp_tools = data.get("result", {}).get("tools", [])

        # Convert to Claude tool format
        self.claude_tools = [
            self._mcp_to_claude_tool(tool) for tool in self.mcp_tools
        ]

        print(f"Loaded {len(self.claude_tools)} tools")

    def _mcp_to_claude_tool(self, mcp_tool: Dict) -> Dict:
        """Convert MCP tool schema to Claude tool format"""
        return {
            "name": mcp_tool["name"],
            "description": mcp_tool.get("description", ""),
            "input_schema": mcp_tool.get("inputSchema", {
                "type": "object",
                "properties": {}
            })
        }

    async def call_tool(self, name: str, arguments: Dict) -> str:
        """Execute a tool via MCP and return result"""
        async with aiohttp.ClientSession() as session:
            request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments
                }
            }

            async with session.post(
                f"{self.mcp_url}/mcp",
                json=request,
                headers={"X-Session-ID": self.session_id}
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    return f"Error: {data['error'].get('message', 'Unknown error')}"

                result = data.get("result", {})
                content = result.get("content", [])

                if content and content[0].get("type") == "text":
                    return content[0].get("text", "")

                return json.dumps(result)

    async def chat(self, user_message: str) -> str:
        """
        Send a message to Claude and handle tool calls.

        This implements the full conversation loop:
        1. Send user message to Claude with available tools
        2. If Claude wants to use a tool, execute it via MCP
        3. Send tool result back to Claude
        4. Return final response
        """
        messages = [{"role": "user", "content": user_message}]

        while True:
            # Call Claude
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                tools=self.claude_tools,
                messages=messages
            )

            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Process tool calls
                assistant_content = response.content
                tool_results = []

                for block in assistant_content:
                    if block.type == "tool_use":
                        print(f"  → Calling tool: {block.name}")
                        result = await self.call_tool(block.name, block.input)
                        print(f"  ← Result: {result[:100]}...")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                # Add assistant message and tool results
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})

            else:
                # No more tool calls, return final response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                return final_text


async def main():
    """Demo: Chat with Claude using MCP tools"""

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Please set ANTHROPIC_API_KEY environment variable")
        return

    print("=" * 60)
    print("Claude + MCP Integration Demo")
    print("=" * 60)

    # Connect to MCP
    adapter = MCPClaudeAdapter("http://localhost:8000")

    try:
        await adapter.connect()
    except Exception as e:
        print(f"\nError connecting to MCP server: {e}")
        print("Make sure the MCP server is running:")
        print("  python ../mcp_server.py")
        return

    print("\nAvailable tools:")
    for tool in adapter.claude_tools:
        print(f"  • {tool['name']}: {tool['description'][:50]}...")

    # Demo conversations
    demo_messages = [
        "What time is it right now?",
        "Can you add a note saying 'Remember to review MCP integration'?",
        "What's 42 multiplied by 17?",
        "Show me all my notes",
    ]

    print("\n" + "=" * 60)
    print("Demo Conversations")
    print("=" * 60)

    for msg in demo_messages:
        print(f"\nUser: {msg}")
        response = await adapter.chat(msg)
        print(f"Claude: {response}")

    # Interactive mode
    print("\n" + "=" * 60)
    print("Interactive Mode (type 'quit' to exit)")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            if not user_input:
                continue

            response = await adapter.chat(user_input)
            print(f"Claude: {response}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(main())
