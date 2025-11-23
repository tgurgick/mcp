#!/usr/bin/env python3
"""
Example MCP Server with Real-World Tools

This server demonstrates practical tool implementations:
- File operations (read, list, search)
- HTTP requests
- Data transformation
- System information

Usage:
    python example_server.py --port 8000
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import MCPServer, StreamableHTTPTransport, MCPSession


class ExampleServer(MCPServer):
    """MCP Server with practical example tools"""

    def __init__(self):
        super().__init__(name="example-mcp-server", version="1.0.0")
        self._register_example_tools()
        self._register_example_resources()

    def _register_example_tools(self):
        """Register example tools with real-world use cases"""

        # File Operations
        self._tools["read_file"] = {
            "name": "read_file",
            "description": "Read contents of a file. Supports text files.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum lines to read (default: 100)",
                        "default": 100
                    }
                },
                "required": ["path"]
            }
        }

        self._tools["list_directory"] = {
            "name": "list_directory",
            "description": "List files and directories in a path",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list",
                        "default": "."
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter (e.g., '*.py')"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List recursively",
                        "default": False
                    }
                }
            }
        }

        self._tools["search_files"] = {
            "name": "search_files",
            "description": "Search for text pattern in files",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in",
                        "default": "."
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File glob pattern (e.g., '*.py')",
                        "default": "*"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20
                    }
                },
                "required": ["pattern"]
            }
        }

        # HTTP Tools
        self._tools["http_get"] = {
            "name": "http_get",
            "description": "Make an HTTP GET request to a URL",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch"
                    },
                    "headers": {
                        "type": "object",
                        "description": "Optional headers to send"
                    }
                },
                "required": ["url"]
            }
        }

        # Data Tools
        self._tools["json_query"] = {
            "name": "json_query",
            "description": "Query JSON data using a simple path expression",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "JSON string to query"
                    },
                    "path": {
                        "type": "string",
                        "description": "Path expression (e.g., 'users.0.name')"
                    }
                },
                "required": ["data", "path"]
            }
        }

        self._tools["transform_data"] = {
            "name": "transform_data",
            "description": "Transform data between formats (JSON, CSV, YAML)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "Input data"
                    },
                    "from_format": {
                        "type": "string",
                        "enum": ["json", "csv"],
                        "description": "Input format"
                    },
                    "to_format": {
                        "type": "string",
                        "enum": ["json", "csv", "markdown_table"],
                        "description": "Output format"
                    }
                },
                "required": ["data", "from_format", "to_format"]
            }
        }

        # System Tools
        self._tools["system_info"] = {
            "name": "system_info",
            "description": "Get system information",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }

        self._tools["run_command"] = {
            "name": "run_command",
            "description": "Run a shell command (read-only commands only)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to run"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 30
                    }
                },
                "required": ["command"]
            }
        }

    def _register_example_resources(self):
        """Register example resources"""
        self._resources["system://info"] = {
            "uri": "system://info",
            "name": "System Information",
            "description": "Current system information",
            "mimeType": "application/json"
        }

        self._resources["env://variables"] = {
            "uri": "env://variables",
            "name": "Environment Variables",
            "description": "Safe environment variables",
            "mimeType": "application/json"
        }

    async def _execute_tool(
        self, name: str, arguments: Dict[str, Any], session: MCPSession
    ) -> Dict[str, Any]:
        """Execute example tools"""

        # File operations
        if name == "read_file":
            return await self._tool_read_file(arguments)

        elif name == "list_directory":
            return await self._tool_list_directory(arguments)

        elif name == "search_files":
            return await self._tool_search_files(arguments)

        # HTTP tools
        elif name == "http_get":
            return await self._tool_http_get(arguments)

        # Data tools
        elif name == "json_query":
            return await self._tool_json_query(arguments)

        elif name == "transform_data":
            return await self._tool_transform_data(arguments)

        # System tools
        elif name == "system_info":
            return await self._tool_system_info(arguments)

        elif name == "run_command":
            return await self._tool_run_command(arguments)

        # Fall back to parent implementation
        return await super()._execute_tool(name, arguments, session)

    # === Tool Implementations ===

    async def _tool_read_file(self, args: Dict) -> Dict:
        """Read file contents"""
        path = Path(args["path"]).expanduser()
        max_lines = args.get("max_lines", 100)

        if not path.exists():
            return {
                "content": [{"type": "text", "text": f"File not found: {path}"}],
                "isError": True
            }

        if not path.is_file():
            return {
                "content": [{"type": "text", "text": f"Not a file: {path}"}],
                "isError": True
            }

        try:
            lines = path.read_text().splitlines()[:max_lines]
            content = "\n".join(lines)

            if len(lines) == max_lines:
                content += f"\n... (truncated at {max_lines} lines)"

            return {"content": [{"type": "text", "text": content}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error reading file: {e}"}],
                "isError": True
            }

    async def _tool_list_directory(self, args: Dict) -> Dict:
        """List directory contents"""
        path = Path(args.get("path", ".")).expanduser()
        pattern = args.get("pattern", "*")
        recursive = args.get("recursive", False)

        if not path.exists():
            return {
                "content": [{"type": "text", "text": f"Path not found: {path}"}],
                "isError": True
            }

        try:
            if recursive:
                items = list(path.rglob(pattern))[:100]
            else:
                items = list(path.glob(pattern))[:100]

            result = []
            for item in sorted(items):
                item_type = "📁" if item.is_dir() else "📄"
                size = item.stat().st_size if item.is_file() else 0
                result.append(f"{item_type} {item.relative_to(path)} ({size} bytes)")

            return {"content": [{"type": "text", "text": "\n".join(result) or "No files found"}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True
            }

    async def _tool_search_files(self, args: Dict) -> Dict:
        """Search for pattern in files"""
        pattern = args["pattern"]
        path = Path(args.get("path", ".")).expanduser()
        file_pattern = args.get("file_pattern", "*")
        max_results = args.get("max_results", 20)

        results = []
        try:
            for file_path in path.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                try:
                    content = file_path.read_text()
                    for i, line in enumerate(content.splitlines(), 1):
                        if pattern.lower() in line.lower():
                            results.append(f"{file_path}:{i}: {line.strip()[:80]}")
                            if len(results) >= max_results:
                                break
                except:
                    continue

                if len(results) >= max_results:
                    break

            return {"content": [{"type": "text", "text": "\n".join(results) or "No matches found"}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True
            }

    async def _tool_http_get(self, args: Dict) -> Dict:
        """Make HTTP GET request"""
        import aiohttp

        url = args["url"]
        headers = args.get("headers", {})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    text = await resp.text()
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Status: {resp.status}\n\n{text[:5000]}"
                        }]
                    }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"HTTP error: {e}"}],
                "isError": True
            }

    async def _tool_json_query(self, args: Dict) -> Dict:
        """Query JSON data"""
        try:
            data = json.loads(args["data"])
            path = args["path"]

            # Simple path resolution (e.g., "users.0.name")
            result = data
            for part in path.split("."):
                if part.isdigit():
                    result = result[int(part)]
                else:
                    result = result[part]

            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Query error: {e}"}],
                "isError": True
            }

    async def _tool_transform_data(self, args: Dict) -> Dict:
        """Transform data between formats"""
        import csv
        import io

        data = args["data"]
        from_fmt = args["from_format"]
        to_fmt = args["to_format"]

        try:
            # Parse input
            if from_fmt == "json":
                parsed = json.loads(data)
            elif from_fmt == "csv":
                reader = csv.DictReader(io.StringIO(data))
                parsed = list(reader)

            # Convert output
            if to_fmt == "json":
                result = json.dumps(parsed, indent=2)
            elif to_fmt == "csv":
                if not parsed:
                    result = ""
                else:
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=parsed[0].keys())
                    writer.writeheader()
                    writer.writerows(parsed)
                    result = output.getvalue()
            elif to_fmt == "markdown_table":
                if not parsed:
                    result = ""
                else:
                    headers = list(parsed[0].keys())
                    result = "| " + " | ".join(headers) + " |\n"
                    result += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                    for row in parsed:
                        result += "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |\n"

            return {"content": [{"type": "text", "text": result}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Transform error: {e}"}],
                "isError": True
            }

    async def _tool_system_info(self, args: Dict) -> Dict:
        """Get system information"""
        import platform

        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "cwd": os.getcwd(),
            "time": datetime.now().isoformat()
        }

        return {"content": [{"type": "text", "text": json.dumps(info, indent=2)}]}

    async def _tool_run_command(self, args: Dict) -> Dict:
        """Run shell command (restricted)"""
        import subprocess

        command = args["command"]
        timeout = args.get("timeout", 30)

        # Safety: block dangerous commands
        dangerous = ["rm", "sudo", "chmod", "chown", "mv", "cp", ">", ">>", "|"]
        if any(d in command.lower() for d in dangerous):
            return {
                "content": [{"type": "text", "text": "Command not allowed for safety reasons"}],
                "isError": True
            }

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = result.stdout or result.stderr or "(no output)"
            return {"content": [{"type": "text", "text": output[:5000]}]}
        except subprocess.TimeoutExpired:
            return {
                "content": [{"type": "text", "text": f"Command timed out after {timeout}s"}],
                "isError": True
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True
            }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Example MCP Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    server = ExampleServer()
    transport = StreamableHTTPTransport(server, host=args.host, port=args.port)
    transport.run()


if __name__ == "__main__":
    main()
