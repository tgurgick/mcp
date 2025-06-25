#!/usr/bin/env python3
"""
Real MCP Client with AI Integration
A client that can interact with the AI-powered MCP server using natural language
"""

import asyncio
import json
import sys
from typing import Dict, Any

class RealMCPClient:
    """Real MCP Client implementation with AI integration."""
    
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
                "name": "real-mcp-client",
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
    
    async def chat(self, message: str) -> str:
        """Send a chat message to the AI and get a response."""
        result = await self.send_request("chat/completions", {"message": message})
        return result["content"][0]["text"]
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        return await self.send_request("tools/list")
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool directly."""
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

async def interactive_chat():
    """Interactive chat mode with the AI-powered MCP server."""
    print("🤖 AI-Powered MCP Server Chat")
    print("=" * 50)
    print("This server uses OpenAI to understand your requests and use tools automatically!")
    print("Type 'quit' to exit, 'tools' to see available tools, 'resources' to see resources")
    print()
    
    client = RealMCPClient("python", ["real_mcp_server.py"])
    
    try:
        # Start the server
        await client.start()
        print("✅ Server started successfully")
        print()
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'tools':
                    result = await client.list_tools()
                    tools = result.get("tools", [])
                    print(f"\nAvailable tools ({len(tools)}):")
                    for tool in tools:
                        print(f"  • {tool['name']}: {tool['description']}")
                    print()
                    continue
                elif user_input.lower() == 'resources':
                    result = await client.list_resources()
                    resources = result.get("resources", [])
                    print(f"\nAvailable resources ({len(resources)}):")
                    for resource in resources:
                        print(f"  • {resource['uri']}: {resource['description']}")
                    print()
                    continue
                
                # Send message to AI
                print("AI: ", end="", flush=True)
                response = await client.chat(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                print()
    
    except Exception as e:
        print(f"❌ Error during chat: {e}")
        raise
    finally:
        await client.stop()
        print("🛑 Server stopped")

async def demo_chat():
    """Demo mode with predefined messages to showcase AI capabilities."""
    print("🎬 AI-Powered MCP Server Demo")
    print("=" * 50)
    
    client = RealMCPClient("python", ["real_mcp_server.py"])
    
    try:
        # Start the server
        await client.start()
        print("✅ Server started successfully")
        print()
        
        # Demo messages
        demo_messages = [
            "Hello! Can you tell me what time it is?",
            "Please add a note that says 'Meeting with team at 3 PM'",
            "What's the weather like in New York?",
            "Can you calculate the sum of 15 and 27?",
            "Show me all my notes",
            "Increment the counter a few times",
            "What's the current counter value?"
        ]
        
        for i, message in enumerate(demo_messages, 1):
            print(f"Demo {i}: {message}")
            print("AI: ", end="", flush=True)
            
            try:
                response = await client.chat(message)
                print(response)
            except Exception as e:
                print(f"Error: {e}")
            
            print("-" * 50)
            await asyncio.sleep(1)  # Brief pause between messages
        
        print("✅ Demo completed!")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        raise
    finally:
        await client.stop()
        print("🛑 Server stopped")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(demo_chat())
    else:
        asyncio.run(interactive_chat()) 