#!/usr/bin/env python3
"""
Simple Test Client for the Basic MCP Server
Demonstrates how to interact with the MCP server using JSON-RPC
"""

import asyncio
import json
import subprocess
import sys
from typing import Dict, Any

class SimpleMCPClient:
    """Simple MCP Client implementation."""
    
    def __init__(self, server_command: str, server_args: list = None):
        self.server_command = server_command
        self.server_args = server_args or []
        self.process = None
        self.request_id = 0
    
    async def start(self):
        """Start the MCP server process."""
        cmd = [self.server_command] + self.server_args
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Initialize the server
        await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {}
            },
            "clientInfo": {
                "name": "simple-mcp-client",
                "version": "1.0.0"
            }
        })
    
    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
    
    def _get_next_id(self) -> int:
        """Get the next request ID."""
        self.request_id += 1
        return self.request_id
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a request to the MCP server."""
        if not self.process:
            raise RuntimeError("Server not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method,
            "params": params or {}
        }
        
        # Send request
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line.encode('utf-8'))
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from server")
        
        response = json.loads(response_line.decode('utf-8').strip())
        
        if "error" in response:
            raise RuntimeError(f"Server error: {response['error']}")
        
        return response.get("result", {})
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        return await self.send_request("tools/list")
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool."""
        return await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
    
    async def list_resources(self) -> Dict[str, Any]:
        """List available resources."""
        return await self.send_request("resources/list")
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource."""
        return await self.send_request("resources/read", {"uri": uri})
    
    async def write_resource(self, uri: str, contents: list) -> Dict[str, Any]:
        """Write to a resource."""
        return await self.send_request("resources/write", {
            "uri": uri,
            "contents": contents
        })

async def test_mcp_server():
    """Test the MCP server functionality."""
    print("🚀 Starting Simple MCP Server Test")
    print("=" * 50)
    
    client = SimpleMCPClient("python", ["simple_mcp_server.py"])
    
    try:
        # Start the server
        await client.start()
        print("✅ Server started successfully")
        
        # Test 1: List available tools
        print("\n📋 Test 1: Listing Available Tools")
        print("-" * 30)
        result = await client.list_tools()
        tools = result.get("tools", [])
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  • {tool['name']}: {tool['description']}")
        
        # Test 2: List available resources
        print("\n📁 Test 2: Listing Available Resources")
        print("-" * 30)
        result = await client.list_resources()
        resources = result.get("resources", [])
        print(f"Found {len(resources)} resources:")
        for resource in resources:
            print(f"  • {resource['uri']}: {resource['description']}")
        
        # Test 3: Call get_current_time tool
        print("\n⏰ Test 3: Getting Current Time")
        print("-" * 30)
        result = await client.call_tool("get_current_time")
        print(f"Result: {result['content'][0]['text']}")
        
        # Test 4: Read user_notes resource
        print("\n📝 Test 4: Reading User Notes")
        print("-" * 30)
        result = await client.read_resource("user_notes")
        print(f"Notes: {result['contents'][0]['text']}")
        
        # Test 5: Add a note
        print("\n✏️ Test 5: Adding a Note")
        print("-" * 30)
        result = await client.call_tool("add_note", {"note": "This is a test note from the client!"})
        print(f"Result: {result['content'][0]['text']}")
        
        # Test 6: Read notes again to see the new note
        print("\n📖 Test 6: Reading Updated Notes")
        print("-" * 30)
        result = await client.read_resource("user_notes")
        print(f"Updated notes: {result['contents'][0]['text']}")
        
        # Test 7: Test counter functionality
        print("\n🔢 Test 7: Testing Counter")
        print("-" * 30)
        for i in range(3):
            result = await client.call_tool("increment_counter")
            print(f"Increment {i+1}: {result['content'][0]['text']}")
        
        # Test 8: Read counter resource
        print("\n📊 Test 8: Reading Counter Resource")
        print("-" * 30)
        result = await client.read_resource("counter")
        print(f"Counter value: {result['contents'][0]['text']}")
        
        # Test 9: Write to a resource
        print("\n✍️ Test 9: Writing to Counter Resource")
        print("-" * 30)
        await client.write_resource("counter", [{"text": "42"}])
        result = await client.read_resource("counter")
        print(f"New counter value: {result['contents'][0]['text']}")
        
        # Test 10: Test calculate_sum tool
        print("\n🧮 Test 10: Testing Calculate Sum Tool")
        print("-" * 30)
        result = await client.call_tool("calculate_sum", {"a": 10, "b": 20})
        print(f"Result: {result['content'][0]['text']}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        raise
    finally:
        await client.stop()
        print("🛑 Server stopped")

async def interactive_test():
    """Interactive test mode for manual testing."""
    print("🎮 Interactive MCP Server Test")
    print("=" * 50)
    
    client = SimpleMCPClient("python", ["simple_mcp_server.py"])
    
    try:
        await client.start()
        print("✅ Server started successfully")
        
        while True:
            print("\nAvailable commands:")
            print("1. list_tools - List all available tools")
            print("2. list_resources - List all available resources")
            print("3. call_tool <tool_name> [args] - Call a tool")
            print("4. read_resource <uri> - Read a resource")
            print("5. write_resource <uri> <text> - Write to a resource")
            print("6. quit - Exit")
            
            command = input("\nEnter command: ").strip().split()
            
            if not command:
                continue
            
            cmd = command[0].lower()
            
            try:
                if cmd == "quit":
                    break
                elif cmd == "list_tools":
                    result = await client.list_tools()
                    tools = result.get("tools", [])
                    print(f"Available tools: {[tool['name'] for tool in tools]}")
                elif cmd == "list_resources":
                    result = await client.list_resources()
                    resources = result.get("resources", [])
                    print(f"Available resources: {[r['uri'] for r in resources]}")
                elif cmd == "call_tool" and len(command) >= 2:
                    tool_name = command[1]
                    args = {}
                    if len(command) > 2:
                        try:
                            args = json.loads(" ".join(command[2:]))
                        except json.JSONDecodeError:
                            print("Invalid JSON arguments")
                            continue
                    
                    result = await client.call_tool(tool_name, args)
                    print(f"Result: {result['content'][0]['text']}")
                elif cmd == "read_resource" and len(command) >= 2:
                    uri = command[1]
                    result = await client.read_resource(uri)
                    print(f"Resource content: {result['contents'][0]['text']}")
                elif cmd == "write_resource" and len(command) >= 3:
                    uri = command[1]
                    text = " ".join(command[2:])
                    await client.write_resource(uri, [{"text": text}])
                    print(f"Written to {uri}: {text}")
                else:
                    print("Invalid command or missing arguments")
            except Exception as e:
                print(f"Error: {e}")
    
    except Exception as e:
        print(f"❌ Error during interactive testing: {e}")
        raise
    finally:
        await client.stop()
        print("🛑 Server stopped")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_test())
    else:
        asyncio.run(test_mcp_server()) 