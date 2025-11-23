#!/usr/bin/env python3
"""
LangChain + MCP Integration Example

This example shows how to:
1. Create LangChain tools from MCP server tools
2. Use MCP tools in LangChain agents
3. Stream responses with tool execution

Requirements:
    pip install langchain langchain-anthropic aiohttp

Usage:
    # Start MCP server first
    python ../mcp_server.py

    # Then run this example
    export ANTHROPIC_API_KEY=your_key
    python langchain_integration.py
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Type

import aiohttp

# Check for required packages
try:
    from langchain.tools import BaseTool
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate
    from langchain.callbacks.base import BaseCallbackHandler
    from pydantic import BaseModel, Field, create_model
except ImportError:
    print("Please install langchain: pip install langchain")
    exit(1)

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    print("Please install langchain-anthropic: pip install langchain-anthropic")
    exit(1)


class MCPToolWrapper(BaseTool):
    """
    Wrapper that converts an MCP tool to a LangChain tool.
    """
    name: str
    description: str
    mcp_url: str
    session_id: Optional[str] = None
    args_schema: Optional[Type[BaseModel]] = None

    def _run(self, **kwargs) -> str:
        """Sync execution - runs async in event loop"""
        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs) -> str:
        """Async execution via MCP"""
        async with aiohttp.ClientSession() as session:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": self.name,
                    "arguments": kwargs
                }
            }

            headers = {"Content-Type": "application/json"}
            if self.session_id:
                headers["X-Session-ID"] = self.session_id

            async with session.post(
                f"{self.mcp_url}/mcp",
                json=request,
                headers=headers
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    return f"Error: {data['error'].get('message', 'Unknown error')}"

                result = data.get("result", {})
                content = result.get("content", [])

                if content and content[0].get("type") == "text":
                    return content[0].get("text", "")

                return json.dumps(result)


def json_schema_to_pydantic(name: str, schema: Dict) -> Type[BaseModel]:
    """
    Convert JSON Schema to Pydantic model for LangChain args_schema.
    """
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields = {}
    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        description = prop_schema.get("description", "")
        default = prop_schema.get("default", ...)

        # Map JSON Schema types to Python types
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        python_type = type_map.get(prop_type, str)

        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            fields[prop_name] = (
                Optional[python_type],
                Field(default=default if default != ... else None, description=description)
            )

    return create_model(f"{name}Args", **fields)


class MCPToolkit:
    """
    Toolkit that loads tools from an MCP server and creates LangChain tools.
    """

    def __init__(self, mcp_url: str = "http://localhost:8000"):
        self.mcp_url = mcp_url.rstrip("/")
        self.session_id: Optional[str] = None
        self.tools: List[MCPToolWrapper] = []

    async def initialize(self):
        """Initialize MCP connection and load tools"""
        async with aiohttp.ClientSession() as session:
            # Initialize MCP connection
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "langchain-adapter", "version": "1.0.0"}
                }
            }

            async with session.post(f"{self.mcp_url}/mcp", json=init_request) as resp:
                self.session_id = resp.headers.get("X-Session-ID")
                data = await resp.json()
                if "error" in data:
                    raise RuntimeError(f"MCP init failed: {data['error']}")

            # Load tools
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            async with session.post(
                f"{self.mcp_url}/mcp",
                json=tools_request,
                headers={"X-Session-ID": self.session_id}
            ) as resp:
                data = await resp.json()
                mcp_tools = data.get("result", {}).get("tools", [])

            # Create LangChain tools
            for tool in mcp_tools:
                args_schema = None
                if "inputSchema" in tool:
                    try:
                        args_schema = json_schema_to_pydantic(
                            tool["name"],
                            tool["inputSchema"]
                        )
                    except Exception:
                        pass  # Fall back to no schema

                lc_tool = MCPToolWrapper(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    mcp_url=self.mcp_url,
                    session_id=self.session_id,
                    args_schema=args_schema
                )
                self.tools.append(lc_tool)

        print(f"Loaded {len(self.tools)} tools from MCP server")
        return self.tools

    def get_tools(self) -> List[MCPToolWrapper]:
        """Get loaded LangChain tools"""
        return self.tools


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming output"""

    def on_llm_start(self, *args, **kwargs):
        print("\n🤖 Thinking...", end="", flush=True)

    def on_llm_end(self, *args, **kwargs):
        print(" done")

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "unknown")
        print(f"\n🔧 Using tool: {tool_name}")
        print(f"   Input: {input_str[:100]}...")

    def on_tool_end(self, output, **kwargs):
        print(f"   Output: {output[:100]}...")


async def create_agent(toolkit: MCPToolkit):
    """Create a LangChain agent with MCP tools"""

    # Initialize the LLM
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0
    )

    # Get tools from MCP
    tools = await toolkit.initialize()

    # Create the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant with access to various tools.
Use tools when needed to answer questions accurately.
Always explain what you're doing."""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # Create executor
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )

    return executor


async def main():
    """Demo: Use MCP tools with LangChain agent"""

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Please set ANTHROPIC_API_KEY environment variable")
        return

    print("=" * 60)
    print("LangChain + MCP Integration Demo")
    print("=" * 60)

    # Create toolkit and agent
    toolkit = MCPToolkit("http://localhost:8000")

    try:
        agent = await create_agent(toolkit)
    except Exception as e:
        print(f"\nError connecting to MCP server: {e}")
        print("Make sure the MCP server is running:")
        print("  python ../mcp_server.py")
        return

    print("\nAvailable tools:")
    for tool in toolkit.get_tools():
        print(f"  • {tool.name}: {tool.description[:50]}...")

    # Demo queries
    demo_queries = [
        "What time is it right now?",
        "Calculate 123 times 456 for me",
        "Add a note saying 'LangChain integration works!'",
    ]

    print("\n" + "=" * 60)
    print("Demo Queries")
    print("=" * 60)

    for query in demo_queries:
        print(f"\n{'─' * 60}")
        print(f"User: {query}")
        print("─" * 60)

        try:
            result = await agent.ainvoke(
                {"input": query},
                config={"callbacks": [StreamingCallbackHandler()]}
            )
            print(f"\nAssistant: {result['output']}")
        except Exception as e:
            print(f"Error: {e}")

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

            result = await agent.ainvoke(
                {"input": user_input},
                config={"callbacks": [StreamingCallbackHandler()]}
            )
            print(f"\nAssistant: {result['output']}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\nGoodbye!")


if __name__ == "__main__":
    asyncio.run(main())
