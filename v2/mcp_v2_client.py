#!/usr/bin/env python3
"""
MCP v2 Client Implementation (2025-06-18 Specification)
Features:
- OAuth 2.0 Authorization Support
- Resource Indicators (RFC 8707)
- Structured Tool Output
- Enhanced Security
- Protocol Version Headers
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPv2Client:
    """MCP v2 Client implementing 2025-06-18 specification"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.protocol_version = "2025-06-18"
        self.session_id = None
        self.access_token = None
        self.resource_indicators = []
        
        # Client capabilities
        self.capabilities = {
            "tools": {},
            "resources": {},
            "prompts": {},
            "sampling": {},
            "roots": {},
            "elicitation": {}
        }
        
        # Initialize connection
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize connection to MCP v2 server"""
        try:
            # Initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": self.capabilities,
                    "clientInfo": {
                        "name": "mcp-v2-client",
                        "version": "2.0.0"
                    }
                },
                "headers": {
                    "MCP-Protocol-Version": self.protocol_version
                }
            }
            
            response = self._send_request(init_request)
            
            if "result" in response:
                result = response["result"]
                self.session_id = result.get("sessionId")
                logger.info(f"Connected to MCP v2 server: {result.get('serverInfo', {}).get('name')}")
                
                # Check OAuth support
                if result.get("oauth", {}).get("supported"):
                    logger.info("Server supports OAuth authorization")
                    self._setup_oauth(result["oauth"]["metadata"])
                else:
                    logger.info("Server does not support OAuth")
            
            elif "error" in response:
                logger.error(f"Initialization failed: {response['error']}")
                raise Exception(f"Failed to initialize: {response['error']['message']}")
        
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            raise

    def _setup_oauth(self, oauth_metadata: Dict[str, Any]):
        """Setup OAuth configuration"""
        self.oauth_metadata = oauth_metadata
        self.resource_indicators = oauth_metadata.get("resource_indicators", [])

    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to MCP server with proper headers"""
        headers = {
            "Content-Type": "application/json",
            "MCP-Protocol-Version": self.protocol_version
        }
        
        # Add authorization header if available
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            response = requests.post(
                self.server_url,
                json=request,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {"error": {"code": -32603, "message": str(e)}}

    def authenticate(self, scope: str = "read", resource_indicators: Optional[List[str]] = None):
        """Authenticate with OAuth"""
        if not hasattr(self, 'oauth_metadata'):
            logger.warning("Server does not support OAuth")
            return False
        
        # Use provided resource indicators or default ones
        indicators = resource_indicators or self.resource_indicators
        
        # Validate resource indicators
        for indicator in indicators:
            if not self._validate_resource_indicator(indicator):
                logger.error(f"Invalid resource indicator: {indicator}")
                return False
        
        auth_request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "oauth/authorize",
            "params": {
                "scope": scope,
                "resource_indicators": indicators
            }
        }
        
        response = self._send_request(auth_request)
        
        if "result" in response:
            result = response["result"]
            self.access_token = result.get("access_token")
            logger.info("Authentication successful")
            return True
        else:
            logger.error(f"Authentication failed: {response.get('error')}")
            return False

    def _validate_resource_indicator(self, indicator: str) -> bool:
        """Validate resource indicator according to RFC 8707"""
        try:
            parsed = urlparse(indicator)
            return parsed.scheme in ["https", "http"] and parsed.netloc
        except:
            return False

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/list",
            "params": {}
        }
        
        response = self._send_request(request)
        
        if "result" in response:
            return response["result"].get("tools", [])
        else:
            logger.error(f"Failed to list tools: {response.get('error')}")
            return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool with arguments"""
        if arguments is None:
            arguments = {}
        
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/call",
            "params": {
                "calls": [
                    {
                        "name": tool_name,
                        "arguments": arguments,
                        "id": f"call_{int(time.time())}"
                    }
                ]
            }
        }
        
        response = self._send_request(request)
        
        if "result" in response:
            calls = response["result"].get("calls", [])
            if calls:
                return calls[0]
            else:
                return {"error": "No tool call results"}
        else:
            logger.error(f"Tool call failed: {response.get('error')}")
            return {"error": response.get('error')}

    def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources"""
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "resources/list",
            "params": {}
        }
        
        response = self._send_request(request)
        
        if "result" in response:
            return response["result"].get("resources", [])
        else:
            logger.error(f"Failed to list resources: {response.get('error')}")
            return []

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource"""
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }
        
        response = self._send_request(request)
        
        if "result" in response:
            return response["result"]
        else:
            logger.error(f"Failed to read resource: {response.get('error')}")
            return {"error": response.get('error')}

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts"""
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "prompts/list",
            "params": {}
        }
        
        response = self._send_request(request)
        
        if "result" in response:
            return response["result"].get("prompts", [])
        else:
            logger.error(f"Failed to list prompts: {response.get('error')}")
            return []

    def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get a prompt with arguments"""
        if arguments is None:
            arguments = {}
        
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "prompts/get",
            "params": {
                "name": name,
                "arguments": arguments
            }
        }
        
        response = self._send_request(request)
        
        if "result" in response:
            return response["result"]
        else:
            logger.error(f"Failed to get prompt: {response.get('error')}")
            return {"error": response.get('error')}

    def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4") -> Dict[str, Any]:
        """Send chat completion request"""
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "chat/completions",
            "params": {
                "messages": messages,
                "model": model
            }
        }
        
        response = self._send_request(request)
        
        if "result" in response:
            return response["result"]
        else:
            logger.error(f"Chat completion failed: {response.get('error')}")
            return {"error": response.get('error')}

    def interactive_chat(self):
        """Interactive chat mode"""
        print("MCP v2 Interactive Chat Mode")
        print("Commands: /tools, /resources, /prompts, /auth, /quit")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                    break
                elif user_input == '/tools':
                    tools = self.list_tools()
                    print("\nAvailable Tools:")
                    for tool in tools:
                        print(f"  - {tool['title']}: {tool['description']}")
                    print()
                elif user_input == '/resources':
                    resources = self.list_resources()
                    print("\nAvailable Resources:")
                    for resource in resources:
                        print(f"  - {resource['title']}: {resource['description']}")
                    print()
                elif user_input == '/prompts':
                    prompts = self.list_prompts()
                    print("\nAvailable Prompts:")
                    for prompt in prompts:
                        print(f"  - {prompt['title']}: {prompt['description']}")
                    print()
                elif user_input == '/auth':
                    if self.authenticate():
                        print("Authentication successful!")
                    else:
                        print("Authentication failed!")
                elif user_input.startswith('/tool '):
                    # Tool call format: /tool tool_name arg1=value1 arg2=value2
                    parts = user_input[6:].split()
                    if len(parts) >= 1:
                        tool_name = parts[0]
                        arguments = {}
                        
                        # Parse arguments
                        for part in parts[1:]:
                            if '=' in part:
                                key, value = part.split('=', 1)
                                # Try to convert to appropriate type
                                try:
                                    if value.lower() in ['true', 'false']:
                                        arguments[key] = value.lower() == 'true'
                                    elif value.isdigit():
                                        arguments[key] = int(value)
                                    elif value.replace('.', '').isdigit():
                                        arguments[key] = float(value)
                                    else:
                                        arguments[key] = value
                                except:
                                    arguments[key] = value
                        
                        result = self.call_tool(tool_name, arguments)
                        if "error" not in result:
                            print(f"Tool Result: {result.get('content', result)}")
                        else:
                            print(f"Tool Error: {result['error']}")
                elif user_input.startswith('/resource '):
                    uri = user_input[10:].strip()
                    result = self.read_resource(uri)
                    if "error" not in result:
                        contents = result.get("contents", [])
                        for content in contents:
                            print(f"Resource ({content.get('mimeType', 'text/plain')}):")
                            print(content.get("text", ""))
                    else:
                        print(f"Resource Error: {result['error']}")
                else:
                    # Regular chat message
                    messages = [{"role": "user", "content": user_input}]
                    response = self.chat_completion(messages)
                    
                    if "error" not in response:
                        choices = response.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            print(f"Assistant: {content}")
                        else:
                            print("Assistant: No response received")
                    else:
                        print(f"Chat Error: {response['error']}")
            
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def demo_mode(self):
        """Demo mode showing v2 features"""
        print("MCP v2 Demo Mode")
        print("=" * 50)
        
        # 1. Show tools
        print("\n1. Available Tools:")
        tools = self.list_tools()
        for tool in tools:
            print(f"  - {tool['title']}: {tool['description']}")
        
        # 2. Show resources
        print("\n2. Available Resources:")
        resources = self.list_resources()
        for resource in resources:
            print(f"  - {resource['title']}: {resource['description']}")
        
        # 3. Show prompts
        print("\n3. Available Prompts:")
        prompts = self.list_prompts()
        for prompt in prompts:
            print(f"  - {prompt['title']}: {prompt['description']}")
        
        # 4. Test authentication
        print("\n4. Testing OAuth Authentication:")
        if self.authenticate():
            print("  ✓ Authentication successful")
        else:
            print("  ✗ Authentication failed")
        
        # 5. Test tool calls
        print("\n5. Testing Tool Calls:")
        
        # Get current time
        result = self.call_tool("get_current_time")
        if "error" not in result:
            print(f"  ✓ {result.get('content', result)}")
        
        # Add a note
        result = self.call_tool("add_note", {"content": "Demo note from MCP v2 client", "tags": ["demo", "v2"]})
        if "error" not in result:
            print(f"  ✓ {result.get('content', result)}")
        
        # Get notes
        result = self.call_tool("get_notes", {"limit": 5})
        if "error" not in result:
            print(f"  ✓ {result.get('content', result)}")
        
        # 6. Test resource reading
        print("\n6. Testing Resource Reading:")
        result = self.read_resource("server_status")
        if "error" not in result:
            contents = result.get("contents", [])
            for content in contents:
                print(f"  ✓ Server Status: {content.get('text', '')[:100]}...")
        
        # 7. Test prompts
        print("\n7. Testing Prompts:")
        result = self.get_prompt("welcome_message", {"user_name": "Demo User"})
        if "error" not in result:
            content = result.get("content", [])
            if content:
                print(f"  ✓ {content[0].get('text', '')}")
        
        print("\nDemo completed!")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP v2 Client")
    parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--mode", choices=["interactive", "demo"], default="interactive", help="Client mode")
    parser.add_argument("--auth", action="store_true", help="Authenticate on startup")
    
    args = parser.parse_args()
    
    try:
        client = MCPv2Client(args.server)
        
        if args.auth:
            print("Authenticating...")
            if client.authenticate():
                print("Authentication successful!")
            else:
                print("Authentication failed!")
        
        if args.mode == "interactive":
            client.interactive_chat()
        elif args.mode == "demo":
            client.demo_mode()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 