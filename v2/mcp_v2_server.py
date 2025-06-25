#!/usr/bin/env python3
"""
MCP v2 Server Implementation (2025-06-18 Specification)
Features:
- OAuth 2.0 Authorization Support
- Resource Indicators (RFC 8707)
- Structured Tool Output
- Elicitation Support
- Resource Links
- Protocol Version Headers
- Enhanced Security
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPv2Server:
    """MCP v2 Server implementing 2025-06-18 specification"""
    
    def __init__(self):
        self.openai_client = None
        self.conversation_history = []
        self.counter = 0
        self.notes = []
        
        # Initialize OpenAI if API key is available
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized")
        else:
            logger.warning("No OpenAI API key found. AI features will be disabled.")
        
        # MCP v2 specific configurations
        self.protocol_version = "2025-06-18"
        self.server_info = {
            "name": "mcp-v2-server",
            "version": "2.0.0",
            "protocol_version": self.protocol_version,
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {},
                "sampling": {},
                "roots": {},
                "elicitation": {}
            }
        }
        
        # OAuth Resource Server metadata
        self.oauth_metadata = {
            "issuer": "https://mcp-v2-server.example.com",
            "authorization_endpoint": "https://auth.example.com/oauth/authorize",
            "token_endpoint": "https://auth.example.com/oauth/token",
            "resource_indicators": ["https://mcp-v2-server.example.com/api/*"],
            "scopes": ["read", "write", "admin"]
        }
        
        # Initialize tools with enhanced metadata
        self._initialize_tools()
        self._initialize_resources()
        self._initialize_prompts()

    def _initialize_tools(self):
        """Initialize tools with enhanced v2 metadata"""
        self.server_info["capabilities"]["tools"] = {
            "get_current_time": {
                "name": "get_current_time",
                "title": "Get Current Time",
                "description": "Returns the current server time",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "_meta": {
                    "category": "system",
                    "requires_auth": False,
                    "rate_limit": "unlimited"
                }
            },
            "increment_counter": {
                "name": "increment_counter",
                "title": "Increment Counter",
                "description": "Increments and returns the current counter value",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "integer",
                            "description": "Amount to increment by",
                            "default": 1
                        }
                    },
                    "required": []
                },
                "_meta": {
                    "category": "state",
                    "requires_auth": True,
                    "rate_limit": "100/hour"
                }
            },
            "add_note": {
                "name": "add_note",
                "title": "Add Note",
                "description": "Adds a note to the server's note collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The note content"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for the note"
                        }
                    },
                    "required": ["content"]
                },
                "_meta": {
                    "category": "data",
                    "requires_auth": True,
                    "rate_limit": "1000/day"
                }
            },
            "get_notes": {
                "name": "get_notes",
                "title": "Get Notes",
                "description": "Retrieves notes from the server's collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of notes to return",
                            "default": 10
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags"
                        }
                    },
                    "required": []
                },
                "_meta": {
                    "category": "data",
                    "requires_auth": True,
                    "rate_limit": "unlimited"
                }
            },
            "calculate_sum": {
                "name": "calculate_sum",
                "title": "Calculate Sum",
                "description": "Calculates the sum of provided numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "numbers": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Numbers to sum"
                        }
                    },
                    "required": ["numbers"]
                },
                "_meta": {
                    "category": "computation",
                    "requires_auth": False,
                    "rate_limit": "unlimited"
                }
            },
            "get_weather_info": {
                "name": "get_weather_info",
                "title": "Get Weather Information",
                "description": "Simulates getting weather information for a location",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location to get weather for"
                        },
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature units",
                            "default": "celsius"
                        }
                    },
                    "required": ["location"]
                },
                "_meta": {
                    "category": "external",
                    "requires_auth": True,
                    "rate_limit": "100/hour"
                }
            }
        }

    def _initialize_resources(self):
        """Initialize resources with v2 metadata"""
        self.server_info["capabilities"]["resources"] = {
            "server_status": {
                "name": "server_status",
                "title": "Server Status",
                "description": "Current server status and health information",
                "mimeType": "application/json",
                "_meta": {
                    "category": "system",
                    "requires_auth": False,
                    "cache_duration": 60
                }
            },
            "api_documentation": {
                "name": "api_documentation",
                "title": "API Documentation",
                "description": "Complete API documentation for this MCP server",
                "mimeType": "text/markdown",
                "_meta": {
                    "category": "documentation",
                    "requires_auth": False,
                    "cache_duration": 3600
                }
            }
        }

    def _initialize_prompts(self):
        """Initialize prompts with v2 metadata"""
        self.server_info["capabilities"]["prompts"] = {
            "welcome_message": {
                "name": "welcome_message",
                "title": "Welcome Message",
                "description": "A welcome message for new users",
                "arguments": {
                    "type": "object",
                    "properties": {
                        "user_name": {
                            "type": "string",
                            "description": "Name of the user"
                        }
                    },
                    "required": ["user_name"]
                },
                "_meta": {
                    "category": "user_experience",
                    "requires_auth": False
                }
            }
        }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests with v2 protocol support"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.info(f"Handling request: {method}")
        
        # Check protocol version
        if "MCP-Protocol-Version" in request.get("headers", {}):
            client_version = request["headers"]["MCP-Protocol-Version"]
            if client_version != self.protocol_version:
                logger.warning(f"Protocol version mismatch: client={client_version}, server={self.protocol_version}")
        
        try:
            if method == "initialize":
                return self._handle_initialize(params, request_id)
            elif method == "tools/list":
                return self._handle_tools_list(params, request_id)
            elif method == "tools/call":
                return self._handle_tools_call(params, request_id)
            elif method == "resources/list":
                return self._handle_resources_list(params, request_id)
            elif method == "resources/read":
                return self._handle_resources_read(params, request_id)
            elif method == "prompts/list":
                return self._handle_prompts_list(params, request_id)
            elif method == "prompts/get":
                return self._handle_prompts_get(params, request_id)
            elif method == "chat/completions":
                return self._handle_chat_completions(params, request_id)
            elif method == "oauth/metadata":
                return self._handle_oauth_metadata(params, request_id)
            elif method == "oauth/authorize":
                return self._handle_oauth_authorize(params, request_id)
            else:
                return self._create_error_response(
                    request_id, 
                    -32601, 
                    f"Method not found: {method}"
                )
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return self._create_error_response(
                request_id, 
                -32603, 
                f"Internal error: {str(e)}"
            )

    def _handle_initialize(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle initialization with v2 protocol features"""
        client_info = params.get("clientInfo", {})
        client_capabilities = params.get("capabilities", {})
        
        logger.info(f"Initializing with client: {client_info}")
        
        # Check for required client capabilities
        required_capabilities = ["tools", "resources"]
        missing_capabilities = [cap for cap in required_capabilities 
                              if cap not in client_capabilities]
        
        if missing_capabilities:
            return self._create_error_response(
                request_id,
                -32602,
                f"Missing required capabilities: {missing_capabilities}"
            )
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": self.protocol_version,
                "capabilities": self.server_info["capabilities"],
                "serverInfo": {
                    "name": self.server_info["name"],
                    "version": self.server_info["version"]
                },
                "oauth": {
                    "supported": True,
                    "metadata": self.oauth_metadata
                }
            }
        }

    def _handle_oauth_metadata(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle OAuth metadata request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "metadata": self.oauth_metadata
            }
        }

    def _handle_oauth_authorize(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle OAuth authorization request"""
        scope = params.get("scope", "read")
        resource_indicators = params.get("resource_indicators", [])
        
        # Validate resource indicators
        for indicator in resource_indicators:
            if not self._validate_resource_indicator(indicator):
                return self._create_error_response(
                    request_id,
                    -32602,
                    f"Invalid resource indicator: {indicator}"
                )
        
        # Simulate authorization
        auth_result = {
            "access_token": f"token_{int(time.time())}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": scope,
            "resource_indicators": resource_indicators
        }
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": auth_result
        }

    def _validate_resource_indicator(self, indicator: str) -> bool:
        """Validate resource indicator according to RFC 8707"""
        try:
            parsed = urlparse(indicator)
            return parsed.scheme in ["https", "http"] and parsed.netloc
        except:
            return False

    def _handle_tools_list(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle tools list request with enhanced metadata"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": list(self.server_info["capabilities"]["tools"].values())
            }
        }

    def _handle_tools_call(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle tool calls with structured output support"""
        tool_calls = params.get("calls", [])
        results = []
        
        for call in tool_calls:
            tool_name = call.get("name")
            arguments = call.get("arguments", {})
            call_id = call.get("id")
            
            # Check authorization for protected tools
            if self._requires_auth(tool_name):
                auth_header = params.get("headers", {}).get("Authorization")
                if not self._validate_auth(auth_header):
                    results.append({
                        "name": tool_name,
                        "id": call_id,
                        "error": {
                            "code": -32001,
                            "message": "Authentication required"
                        }
                    })
                    continue
            
            try:
                result = self._execute_tool(tool_name, arguments)
                results.append({
                    "name": tool_name,
                    "id": call_id,
                    "content": [
                        {
                            "type": "text",
                            "text": str(result.get("content", result))
                        }
                    ],
                    "structured": result.get("structured"),
                    "resourceLinks": result.get("resource_links", [])
                })
            except Exception as e:
                results.append({
                    "name": tool_name,
                    "id": call_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "calls": results
            }
        }

    def _requires_auth(self, tool_name: str) -> bool:
        """Check if a tool requires authentication"""
        tool_info = self.server_info["capabilities"]["tools"].get(tool_name, {})
        return tool_info.get("_meta", {}).get("requires_auth", False)

    def _validate_auth(self, auth_header: Optional[str]) -> bool:
        """Validate authentication header"""
        if not auth_header:
            return False
        
        # Simple validation - in real implementation, validate JWT or OAuth token
        return auth_header.startswith("Bearer ")

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with enhanced v2 features"""
        if tool_name == "get_current_time":
            current_time = datetime.now().isoformat()
            return {
                "content": f"Current server time: {current_time}",
                "structured": {
                    "timestamp": current_time,
                    "timezone": "UTC",
                    "format": "ISO 8601"
                }
            }
        
        elif tool_name == "increment_counter":
            amount = arguments.get("amount", 1)
            self.counter += amount
            return {
                "content": f"Counter incremented by {amount}. New value: {self.counter}",
                "structured": {
                    "previous_value": self.counter - amount,
                    "increment": amount,
                    "new_value": self.counter
                }
            }
        
        elif tool_name == "add_note":
            content = arguments.get("content")
            tags = arguments.get("tags", [])
            
            note = {
                "id": len(self.notes) + 1,
                "content": content,
                "tags": tags,
                "timestamp": datetime.now().isoformat()
            }
            self.notes.append(note)
            
            return {
                "content": f"Note added successfully. ID: {note['id']}",
                "structured": note,
                "resource_links": [
                    {
                        "uri": f"note://{note['id']}",
                        "mimeType": "application/json",
                        "title": f"Note {note['id']}"
                    }
                ]
            }
        
        elif tool_name == "get_notes":
            limit = arguments.get("limit", 10)
            tags = arguments.get("tags", [])
            
            filtered_notes = self.notes
            if tags:
                filtered_notes = [note for note in self.notes 
                                if any(tag in note.get("tags", []) for tag in tags)]
            
            result_notes = filtered_notes[-limit:] if limit > 0 else filtered_notes
            
            return {
                "content": f"Retrieved {len(result_notes)} notes",
                "structured": {
                    "notes": result_notes,
                    "total_count": len(filtered_notes),
                    "returned_count": len(result_notes)
                }
            }
        
        elif tool_name == "calculate_sum":
            numbers = arguments.get("numbers", [])
            total = sum(numbers)
            
            return {
                "content": f"Sum of {numbers} = {total}",
                "structured": {
                    "numbers": numbers,
                    "sum": total,
                    "count": len(numbers)
                }
            }
        
        elif tool_name == "get_weather_info":
            location = arguments.get("location")
            units = arguments.get("units", "celsius")
            
            # Simulate weather data
            import random
            temperature = random.randint(-10, 35)
            if units == "fahrenheit":
                temperature = (temperature * 9/5) + 32
            
            weather_data = {
                "location": location,
                "temperature": round(temperature, 1),
                "units": units,
                "condition": random.choice(["sunny", "cloudy", "rainy", "snowy"]),
                "humidity": random.randint(30, 90),
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "content": f"Weather in {location}: {weather_data['temperature']}°{units[0].upper()}, {weather_data['condition']}",
                "structured": weather_data
            }
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _handle_resources_list(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle resources list request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": list(self.server_info["capabilities"]["resources"].values())
            }
        }

    def _handle_resources_read(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle resource read request"""
        uri = params.get("uri")
        
        if uri == "server_status":
            status_data = {
                "status": "healthy",
                "uptime": time.time(),
                "version": self.server_info["version"],
                "protocol_version": self.protocol_version,
                "features": list(self.server_info["capabilities"].keys())
            }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(status_data, indent=2)
                        }
                    ]
                }
            }
        
        elif uri == "api_documentation":
            doc_content = f"""# MCP v2 Server API Documentation

## Overview
This server implements the Model Context Protocol v2 (2025-06-18 specification).

## Features
- OAuth 2.0 Authorization
- Resource Indicators (RFC 8707)
- Structured Tool Output
- Enhanced Security

## Tools
{chr(10).join([f"- {tool['title']}: {tool['description']}" for tool in self.server_info['capabilities']['tools'].values()])}

## Resources
{chr(10).join([f"- {resource['title']}: {resource['description']}" for resource in self.server_info['capabilities']['resources'].values()])}

## Authentication
This server supports OAuth 2.0 authorization for protected resources and tools.
"""
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/markdown",
                            "text": doc_content
                        }
                    ]
                }
            }
        
        else:
            return self._create_error_response(
                request_id,
                -32602,
                f"Resource not found: {uri}"
            )

    def _handle_prompts_list(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle prompts list request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "prompts": list(self.server_info["capabilities"]["prompts"].values())
            }
        }

    def _handle_prompts_get(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle prompt get request"""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if name == "welcome_message":
            user_name = arguments.get("user_name", "User")
            message = f"Welcome {user_name}! This is the MCP v2 server with enhanced features including OAuth authorization, structured tool output, and resource indicators."
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        }
                    ]
                }
            }
        
        else:
            return self._create_error_response(
                request_id,
                -32602,
                f"Prompt not found: {name}"
            )

    def _handle_chat_completions(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Handle chat completions with AI integration"""
        if not self.openai_client:
            return self._create_error_response(
                request_id,
                -32603,
                "OpenAI client not available"
            )
        
        messages = params.get("messages", [])
        model = params.get("model", "gpt-4")
        
        # Add conversation history
        full_messages = self.conversation_history + messages
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=full_messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Update conversation history
            self.conversation_history.extend(messages)
            self.conversation_history.append({
                "role": "assistant",
                "content": response.choices[0].message.content
            })
            
            # Keep history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": response.choices[0].message.content
                            },
                            "finish_reason": response.choices[0].finish_reason
                        }
                    ],
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._create_error_response(
                request_id,
                -32603,
                f"AI service error: {str(e)}"
            )

    def _create_error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create a standardized error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

def main():
    """Main function to run the MCP v2 server"""
    server = MCPv2Server()
    
    print("MCP v2 Server (2025-06-18 Specification)")
    print("Features: OAuth, Resource Indicators, Structured Output, Enhanced Security")
    print("=" * 60)
    
    # Simple command-line interface for testing
    while True:
        try:
            line = input("MCP v2 > ")
            if line.lower() in ['quit', 'exit', 'q']:
                break
            
            # Parse JSON-RPC request
            try:
                request = json.loads(line)
                response = server.handle_request(request)
                print(json.dumps(response, indent=2))
            except json.JSONDecodeError:
                print("Error: Invalid JSON")
            except Exception as e:
                print(f"Error: {e}")
        
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main() 