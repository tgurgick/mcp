#!/usr/bin/env python3
"""
MCP Quick Start & CLI

A command-line tool for working with MCP servers:
- Quick setup and verification
- Server management
- Tool development scaffolding
- Diagnostics and testing

Usage:
    python mcp_cli.py setup              # First-time setup
    python mcp_cli.py start              # Start server
    python mcp_cli.py test               # Run diagnostics
    python mcp_cli.py new-tool my_tool   # Scaffold a new tool
    python mcp_cli.py demo               # Run interactive demo
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ANSI colors
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def color(text: str, c: str) -> str:
    if sys.stdout.isatty():
        return f"{c}{text}{Colors.RESET}"
    return text

def print_header(text: str):
    print(color(f"\n{'═' * 60}", Colors.CYAN))
    print(color(f"  {text}", Colors.BOLD))
    print(color(f"{'═' * 60}\n", Colors.CYAN))

def print_step(num: int, text: str):
    print(color(f"  [{num}] ", Colors.BLUE) + text)

def print_success(text: str):
    print(color("  ✓ ", Colors.GREEN) + text)

def print_error(text: str):
    print(color("  ✗ ", Colors.RED) + text)

def print_warn(text: str):
    print(color("  ⚠ ", Colors.YELLOW) + text)


# =============================================================================
# SETUP COMMAND
# =============================================================================

def cmd_setup(args):
    """First-time setup: install dependencies, verify environment"""
    print_header("MCP Quick Setup")

    # Step 1: Check Python version
    print_step(1, "Checking Python version...")
    version = sys.version_info
    if version >= (3, 9):
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        print_error(f"Python 3.9+ required (found {version.major}.{version.minor})")
        return 1

    # Step 2: Install dependencies
    print_step(2, "Installing dependencies...")
    req_file = Path(__file__).parent.parent / "requirements.txt"
    if req_file.exists():
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
            capture_output=True
        )
        if result.returncode == 0:
            print_success("Dependencies installed")
        else:
            print_error(f"pip install failed: {result.stderr.decode()}")
            return 1
    else:
        print_warn("requirements.txt not found, skipping")

    # Step 3: Verify imports
    print_step(3, "Verifying imports...")
    try:
        import aiohttp
        import pydantic
        print_success("Core dependencies OK")
    except ImportError as e:
        print_error(f"Missing dependency: {e}")
        return 1

    # Step 4: Check optional dependencies
    print_step(4, "Checking optional dependencies...")
    optional = []
    try:
        import opentelemetry
        optional.append("opentelemetry")
    except ImportError:
        pass
    try:
        import prometheus_client
        optional.append("prometheus")
    except ImportError:
        pass

    if optional:
        print_success(f"Optional: {', '.join(optional)}")
    else:
        print_warn("No optional dependencies (observability disabled)")

    # Step 5: Create .env if needed
    print_step(5, "Checking environment...")
    env_file = Path(__file__).parent.parent / ".env"
    env_example = Path(__file__).parent.parent / "env.example"

    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print_success("Created .env from template")
    elif env_file.exists():
        print_success(".env exists")
    else:
        print_warn("No .env file (may need for some features)")

    # Step 6: Quick server test
    print_step(6, "Testing server import...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from mcp_server import MCPServer
        print_success("Server module loads OK")
    except Exception as e:
        print_error(f"Server import failed: {e}")
        return 1

    print(color("\n✓ Setup complete! ", Colors.GREEN) + "Try these commands:")
    print(f"  {color('python mcp_cli.py start', Colors.CYAN)}    - Start the server")
    print(f"  {color('python mcp_cli.py demo', Colors.CYAN)}     - Run interactive demo")
    print(f"  {color('python mcp_cli.py test', Colors.CYAN)}     - Run diagnostics")

    return 0


# =============================================================================
# START COMMAND
# =============================================================================

def cmd_start(args):
    """Start the MCP server"""
    print_header("Starting MCP Server")

    server_file = Path(__file__).parent / "mcp_server.py"
    if args.observable:
        server_file = Path(__file__).parent / "mcp_server_observable.py"

    if not server_file.exists():
        print_error(f"Server file not found: {server_file}")
        return 1

    cmd = [sys.executable, str(server_file)]
    if args.port:
        cmd.extend(["--port", str(args.port)])
    if args.host:
        cmd.extend(["--host", args.host])

    host = args.host or "localhost"
    port = args.port or 8000
    print(f"  Server: {color(str(server_file.name), Colors.CYAN)}")
    print(f"  URL: {color(f'http://{host}:{port}', Colors.BLUE)}")
    print(f"  Press {color('Ctrl+C', Colors.YELLOW)} to stop\n")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n" + color("Server stopped", Colors.YELLOW))

    return 0


# =============================================================================
# TEST COMMAND
# =============================================================================

def cmd_test(args):
    """Run diagnostic tests"""
    print_header("Running MCP Diagnostics")

    diag_file = Path(__file__).parent / "mcp_diagnostics.py"
    if not diag_file.exists():
        print_error("mcp_diagnostics.py not found")
        return 1

    cmd = [sys.executable, str(diag_file)]
    if args.server:
        cmd.extend(["--server", args.server])
    if args.verbose:
        cmd.append("-v")
    if args.category:
        cmd.extend(["--tests", args.category])

    return subprocess.run(cmd).returncode


# =============================================================================
# DEMO COMMAND
# =============================================================================

def cmd_demo(args):
    """Run interactive demo"""
    print_header("MCP Interactive Demo")

    client_file = Path(__file__).parent / "mcp_client.py"
    if not client_file.exists():
        print_error("mcp_client.py not found")
        return 1

    cmd = [sys.executable, str(client_file), "--mode", "demo"]
    if args.server:
        cmd.extend(["--server", args.server])

    return subprocess.run(cmd).returncode


# =============================================================================
# NEW-TOOL COMMAND
# =============================================================================

TOOL_TEMPLATE = '''"""
Custom MCP Tool: {name}

This tool was generated by `mcp_cli.py new-tool {name}`

To use this tool:
1. Import it in your server
2. Register it in _register_builtin_tools()
3. Add execution logic in _execute_tool()
"""

# Tool definition (add to MCPServer._register_builtin_tools)
{upper_name}_TOOL = {{
    "name": "{name}",
    "description": "{description}",
    "inputSchema": {{
        "type": "object",
        "properties": {{
            "input": {{
                "type": "string",
                "description": "Input parameter"
            }},
            "options": {{
                "type": "object",
                "description": "Optional settings",
                "properties": {{
                    "verbose": {{"type": "boolean", "default": False}}
                }}
            }}
        }},
        "required": ["input"]
    }}
}}


# Tool execution (add to MCPServer._execute_tool)
async def execute_{name}(arguments: dict) -> dict:
    """
    Execute the {name} tool.

    Args:
        arguments: Tool arguments from the client

    Returns:
        MCP tool result with content
    """
    input_value = arguments.get("input", "")
    options = arguments.get("options", {{}})
    verbose = options.get("verbose", False)

    # TODO: Implement your tool logic here
    result = f"Processed: {{input_value}}"

    if verbose:
        result += " (verbose mode)"

    return {{
        "content": [
            {{
                "type": "text",
                "text": result
            }}
        ]
    }}


# Example usage in mcp_server.py:
#
# 1. In _register_builtin_tools():
#     self._tools["{name}"] = {upper_name}_TOOL
#
# 2. In _execute_tool():
#     elif name == "{name}":
#         return await execute_{name}(arguments)
'''


def cmd_new_tool(args):
    """Scaffold a new custom tool"""
    print_header(f"Creating Tool: {args.name}")

    # Validate name
    if not args.name.isidentifier():
        print_error(f"Invalid tool name: {args.name}")
        print("  Tool names must be valid Python identifiers")
        return 1

    # Create tools directory
    tools_dir = Path(__file__).parent / "tools"
    tools_dir.mkdir(exist_ok=True)

    # Create __init__.py
    init_file = tools_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Custom MCP Tools"""\n')

    # Create tool file
    tool_file = tools_dir / f"{args.name}.py"
    if tool_file.exists() and not args.force:
        print_error(f"Tool already exists: {tool_file}")
        print("  Use --force to overwrite")
        return 1

    description = args.description or f"Custom tool: {args.name}"
    content = TOOL_TEMPLATE.format(
        name=args.name,
        upper_name=args.name.upper(),
        description=description
    )

    tool_file.write_text(content)
    print_success(f"Created {tool_file}")

    print(f"\n  Next steps:")
    print(f"  1. Edit {color(str(tool_file), Colors.CYAN)} to implement your logic")
    print(f"  2. Import and register in mcp_server.py")
    print(f"  3. Test with: {color(f'python mcp_cli.py test', Colors.CYAN)}")

    return 0


# =============================================================================
# NEW-PROJECT COMMAND
# =============================================================================

PROJECT_TEMPLATE = {
    "server.py": '''#!/usr/bin/env python3
"""
{name} - Custom MCP Server

Generated by `mcp_cli.py new-project {name}`
"""

import sys
sys.path.insert(0, "..")  # Allow importing from v3

from mcp_server import MCPServer, StreamableHTTPTransport

class {class_name}Server(MCPServer):
    """Custom MCP server for {name}"""

    def __init__(self):
        super().__init__(name="{name}", version="1.0.0")
        self._register_custom_tools()

    def _register_custom_tools(self):
        """Register project-specific tools"""
        self._tools["hello"] = {
            "name": "hello",
            "description": "Say hello",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "default": "World"}
                }
            }
        }

    async def _execute_tool(self, name: str, arguments: dict, session) -> dict:
        if name == "hello":
            who = arguments.get("name", "World")
            return {"content": [{"type": "text", "text": f"Hello, {who}!"}]}
        return await super()._execute_tool(name, arguments, session)


def main():
    server = {class_name}Server()
    transport = StreamableHTTPTransport(server)
    transport.run()


if __name__ == "__main__":
    main()
''',
    "README.md": '''# {name}

Custom MCP server project.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements.txt

# Start server
python server.py

# Test
python ../mcp_cli.py test --server http://localhost:8000
```

## Custom Tools

- `hello`: Say hello to someone

## Adding Tools

1. Define tool schema in `_register_custom_tools()`
2. Add execution logic in `_execute_tool()`
3. Restart server and test
''',
    ".env": '''# Server configuration
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO
'''
}


def cmd_new_project(args):
    """Create a new MCP project"""
    print_header(f"Creating Project: {args.name}")

    # Create project directory
    project_dir = Path(__file__).parent / "projects" / args.name
    if project_dir.exists() and not args.force:
        print_error(f"Project already exists: {project_dir}")
        print("  Use --force to overwrite")
        return 1

    project_dir.mkdir(parents=True, exist_ok=True)

    # Generate class name
    class_name = "".join(word.capitalize() for word in args.name.split("_"))

    # Create files
    for filename, template in PROJECT_TEMPLATE.items():
        content = template.format(name=args.name, class_name=class_name)
        (project_dir / filename).write_text(content)
        print_success(f"Created {filename}")

    print(f"\n  Project created at: {color(str(project_dir), Colors.CYAN)}")
    print(f"\n  Get started:")
    print(f"  cd {project_dir}")
    print(f"  python server.py")

    return 0


# =============================================================================
# CONNECT COMMAND
# =============================================================================

def cmd_connect(args):
    """Connect to an MCP server interactively"""
    print_header("MCP Interactive Client")

    client_file = Path(__file__).parent / "mcp_client.py"
    cmd = [sys.executable, str(client_file)]
    if args.server:
        cmd.extend(["--server", args.server])

    return subprocess.run(cmd).returncode


# =============================================================================
# STATUS COMMAND
# =============================================================================

def cmd_status(args):
    """Check server status"""
    import urllib.request
    import urllib.error
    import json

    server = args.server or "http://localhost:8000"
    print_header("Server Status")

    print(f"  Checking {color(server, Colors.BLUE)}...\n")

    # Check health
    try:
        with urllib.request.urlopen(f"{server}/health", timeout=5) as response:
            data = json.loads(response.read())
            print_success(f"Health: {data.get('status', 'unknown')}")
            print(f"        Server: {data.get('server', 'unknown')}")
            print(f"        Version: {data.get('version', 'unknown')}")
    except urllib.error.URLError as e:
        print_error(f"Cannot connect: {e.reason}")
        return 1
    except Exception as e:
        print_error(f"Error: {e}")
        return 1

    # Check MCP endpoint
    try:
        req = urllib.request.Request(
            f"{server}/mcp",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            print_success("MCP endpoint: OK")
    except Exception as e:
        print_warn(f"MCP endpoint: {e}")

    return 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="MCP CLI - Development toolkit for Model Context Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  setup         First-time setup and verification
  start         Start the MCP server
  test          Run diagnostic tests
  demo          Run interactive demo
  connect       Connect to server interactively
  status        Check server status
  new-tool      Create a new custom tool
  new-project   Create a new MCP project

Examples:
  %(prog)s setup
  %(prog)s start --port 8000
  %(prog)s test --server http://localhost:8000
  %(prog)s new-tool my_custom_tool --description "Does something cool"
  %(prog)s new-project my_mcp_server
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # setup
    p_setup = subparsers.add_parser("setup", help="First-time setup")
    p_setup.set_defaults(func=cmd_setup)

    # start
    p_start = subparsers.add_parser("start", help="Start MCP server")
    p_start.add_argument("--port", "-p", type=int, help="Server port")
    p_start.add_argument("--host", "-H", help="Server host")
    p_start.add_argument("--observable", "-o", action="store_true",
                         help="Use observable server with tracing")
    p_start.set_defaults(func=cmd_start)

    # test
    p_test = subparsers.add_parser("test", help="Run diagnostics")
    p_test.add_argument("--server", "-s", default="http://localhost:8000")
    p_test.add_argument("--verbose", "-v", action="store_true")
    p_test.add_argument("--category", "-c", help="Test category")
    p_test.set_defaults(func=cmd_test)

    # demo
    p_demo = subparsers.add_parser("demo", help="Run interactive demo")
    p_demo.add_argument("--server", "-s", default="http://localhost:8000")
    p_demo.set_defaults(func=cmd_demo)

    # connect
    p_connect = subparsers.add_parser("connect", help="Connect to server")
    p_connect.add_argument("--server", "-s", default="http://localhost:8000")
    p_connect.set_defaults(func=cmd_connect)

    # status
    p_status = subparsers.add_parser("status", help="Check server status")
    p_status.add_argument("--server", "-s", default="http://localhost:8000")
    p_status.set_defaults(func=cmd_status)

    # new-tool
    p_new_tool = subparsers.add_parser("new-tool", help="Create custom tool")
    p_new_tool.add_argument("name", help="Tool name")
    p_new_tool.add_argument("--description", "-d", help="Tool description")
    p_new_tool.add_argument("--force", "-f", action="store_true")
    p_new_tool.set_defaults(func=cmd_new_tool)

    # new-project
    p_new_project = subparsers.add_parser("new-project", help="Create MCP project")
    p_new_project.add_argument("name", help="Project name")
    p_new_project.add_argument("--force", "-f", action="store_true")
    p_new_project.set_defaults(func=cmd_new_project)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
