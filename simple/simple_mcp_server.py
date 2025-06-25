#!/usr/bin/env python3
"""
Simple MCP Server for AI Agent
A basic implementation of the Model Context Protocol server without external dependencies
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for resources
resources: Dict[str, str] = {
    "current_time": "",
    "user_notes": "Welcome to the simple MCP server!",
    "counter": "0"
}

class SimpleMCPServer:
    """Simple MCP Server implementation."""
    
    def __init__(self):
        self.server_name = "simple-mcp-server"
        self.server_version = "1.0.0"
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools."""
        return [
            {
                "name": "get_current_time",
                "description": "Get the current date and time",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "increment_counter",
                "description": "Increment the counter by 1",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "add_note",
                "description": "Add a note to the user notes",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "note": {
                            "type": "string",
                            "description": "The note to add"
                        }
                    },
                    "required": ["note"]
                }
            },
            {
                "name": "get_notes",
                "description": "Get all user notes",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "calculate_sum",
                "description": "Calculate the sum of two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["a", "b"]
                }
            }
        ]
    
    def get_resources(self) -> List[Dict[str, Any]]:
        """Get available resources."""
        return [
            {
                "uri": "current_time",
                "name": "Current Time",
                "description": "The current date and time",
                "mimeType": "text/plain"
            },
            {
                "uri": "user_notes",
                "name": "User Notes",
                "description": "User's personal notes",
                "mimeType": "text/plain"
            },
            {
                "uri": "counter",
                "name": "Counter",
                "description": "A simple counter value",
                "mimeType": "text/plain"
            }
        ]
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool."""
        try:
            if name == "get_current_time":
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                resources["current_time"] = current_time
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Current time: {current_time}"
                        }
                    ]
                }
            
            elif name == "increment_counter":
                current_count = int(resources.get("counter", "0"))
                new_count = current_count + 1
                resources["counter"] = str(new_count)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Counter incremented! New value: {new_count}"
                        }
                    ]
                }
            
            elif name == "add_note":
                note = arguments.get("note", "")
                if note:
                    current_notes = resources.get("user_notes", "")
                    updated_notes = f"{current_notes}\n- {note}"
                    resources["user_notes"] = updated_notes
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Note added successfully: {note}"
                            }
                        ]
                    }
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "Error: No note provided"
                            }
                        ]
                    }
            
            elif name == "get_notes":
                notes = resources.get("user_notes", "No notes available")
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"User Notes:\n{notes}"
                        }
                    ]
                }
            
            elif name == "calculate_sum":
                a = arguments.get("a", 0)
                b = arguments.get("b", 0)
                result = a + b
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Sum of {a} and {b} is {result}"
                        }
                    ]
                }
            
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Unknown tool: {name}"
                        }
                    ]
                }
        
        except Exception as e:
            logger.error(f"Error in tool call {name}: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing tool {name}: {str(e)}"
                    }
                ]
            }
    
    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource."""
        try:
            if uri in resources:
                content = resources[uri]
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/plain",
                            "text": content
                        }
                    ]
                }
            else:
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/plain",
                            "text": f"Resource '{uri}' not found"
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": f"Error reading resource: {str(e)}"
                    }
                ]
            }
    
    def write_resource(self, uri: str, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Write to a resource."""
        try:
            if contents and len(contents) > 0:
                content = contents[0].get("text", "")
                resources[uri] = content
                return {}
            else:
                return {}
        except Exception as e:
            logger.error(f"Error writing to resource {uri}: {e}")
            return {}

async def handle_mcp_message(server: SimpleMCPServer, message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol messages."""
    method = message.get("method", "")
    params = message.get("params", {})
    id = message.get("id")
    
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": server.server_name,
                        "version": server.server_version
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "tools": server.get_tools()
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = server.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": result
            }
        
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "resources": server.get_resources()
                }
            }
        
        elif method == "resources/read":
            uri = params.get("uri", "")
            result = server.read_resource(uri)
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": result
            }
        
        elif method == "resources/write":
            uri = params.get("uri", "")
            contents = params.get("contents", [])
            result = server.write_resource(uri, contents)
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": result
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return {
            "jsonrpc": "2.0",
            "id": id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

async def main():
    """Main function to run the MCP server."""
    server = SimpleMCPServer()
    
    logger.info("Simple MCP Server started")
    
    try:
        while True:
            # Read a line from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                message = json.loads(line)
                response = await handle_mcp_message(server, message)
                
                # Write response to stdout
                response_line = json.dumps(response) + "\n"
                sys.stdout.write(response_line)
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                error_line = json.dumps(error_response) + "\n"
                sys.stdout.write(error_line)
                sys.stdout.flush()
    
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 