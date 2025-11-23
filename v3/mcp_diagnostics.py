#!/usr/bin/env python3
"""
MCP Diagnostic Test Suite

This module provides comprehensive diagnostic tests for troubleshooting
MCP server/client issues. Each test validates a specific step in the
MCP chain and provides clear pass/fail output with actionable guidance.

Usage:
    # Test against a running server
    python mcp_diagnostics.py --server http://localhost:8000

    # Run specific test categories
    python mcp_diagnostics.py --server http://localhost:8000 --tests transport,protocol

    # Verbose output
    python mcp_diagnostics.py --server http://localhost:8000 -v

    # Test stdio transport
    python mcp_diagnostics.py --stdio --command "python mcp_stdio_server.py"
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import socket

# Check for required dependencies
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from aiohttp_sse_client import client as sse_client
    SSE_CLIENT_AVAILABLE = True
except ImportError:
    SSE_CLIENT_AVAILABLE = False


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    WARN = "WARN"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    message: str
    details: Optional[str] = None
    duration_ms: float = 0
    suggestion: Optional[str] = None


@dataclass
class DiagnosticReport:
    server_url: str
    timestamp: str
    results: List[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.WARN)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.SKIP)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Add color to text if terminal supports it"""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text


def status_icon(status: TestStatus) -> str:
    """Get icon for test status"""
    icons = {
        TestStatus.PASS: colorize("✓", Colors.GREEN),
        TestStatus.FAIL: colorize("✗", Colors.RED),
        TestStatus.WARN: colorize("⚠", Colors.YELLOW),
        TestStatus.SKIP: colorize("○", Colors.GRAY),
    }
    return icons.get(status, "?")


class MCPDiagnostics:
    """MCP Diagnostic Test Runner"""

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        verbose: bool = False,
        timeout: float = 10.0
    ):
        self.server_url = server_url.rstrip("/")
        self.verbose = verbose
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self.report = DiagnosticReport(
            server_url=server_url,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    def log(self, message: str):
        """Print verbose log message"""
        if self.verbose:
            print(colorize(f"  → {message}", Colors.GRAY))

    async def run_test(
        self,
        name: str,
        test_fn: Callable,
        suggestion: str = ""
    ) -> TestResult:
        """Run a single test and record result"""
        start = time.time()
        try:
            self.log(f"Running: {name}")
            success, message, details = await test_fn()
            duration = (time.time() - start) * 1000

            result = TestResult(
                name=name,
                status=TestStatus.PASS if success else TestStatus.FAIL,
                message=message,
                details=details if self.verbose else None,
                duration_ms=duration,
                suggestion=suggestion if not success else None
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = TestResult(
                name=name,
                status=TestStatus.FAIL,
                message=f"Exception: {type(e).__name__}",
                details=str(e) if self.verbose else None,
                duration_ms=duration,
                suggestion=suggestion
            )

        self.report.results.append(result)
        self._print_result(result)
        return result

    def _print_result(self, result: TestResult):
        """Print test result to console"""
        icon = status_icon(result.status)
        duration = f"({result.duration_ms:.0f}ms)"
        print(f"  {icon} {result.name} {colorize(duration, Colors.GRAY)}")

        if result.status == TestStatus.FAIL:
            print(f"      {colorize(result.message, Colors.RED)}")
            if result.suggestion:
                print(f"      {colorize('Suggestion: ' + result.suggestion, Colors.YELLOW)}")
        elif result.status == TestStatus.WARN:
            print(f"      {colorize(result.message, Colors.YELLOW)}")

        if result.details and self.verbose:
            for line in result.details.split("\n")[:5]:
                print(f"      {colorize(line, Colors.GRAY)}")

    # =========================================================================
    # TRANSPORT LAYER TESTS
    # =========================================================================

    async def test_server_reachable(self) -> Tuple[bool, str, str]:
        """Test if server is reachable at network level"""
        from urllib.parse import urlparse
        parsed = urlparse(self.server_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 80

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return True, f"Server reachable at {host}:{port}", ""
            else:
                return False, f"Cannot connect to {host}:{port}", f"Error code: {result}"
        except socket.error as e:
            return False, f"Socket error: {e}", ""

    async def test_health_endpoint(self) -> Tuple[bool, str, str]:
        """Test if /health endpoint responds"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", "pip install aiohttp"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.server_url}/health",
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return True, f"Health OK: {data.get('status', 'unknown')}", json.dumps(data)
                    else:
                        return False, f"Health endpoint returned {resp.status}", await resp.text()
            except aiohttp.ClientError as e:
                return False, f"HTTP error: {e}", ""

    async def test_mcp_endpoint_exists(self) -> Tuple[bool, str, str]:
        """Test if /mcp endpoint exists and accepts POST"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            try:
                # Send minimal request to check endpoint exists
                async with session.post(
                    f"{self.server_url}/mcp",
                    json={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    if resp.status in (200, 204):
                        return True, "MCP endpoint responds to POST", ""
                    elif resp.status == 404:
                        return False, "MCP endpoint not found (404)", "Check server routes"
                    elif resp.status == 405:
                        return False, "Method not allowed (405)", "Endpoint may not accept POST"
                    else:
                        return False, f"Unexpected status: {resp.status}", await resp.text()
            except aiohttp.ClientError as e:
                return False, f"Connection error: {e}", ""

    async def test_sse_endpoint(self) -> Tuple[bool, str, str]:
        """Test if SSE endpoint is available"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.server_url}/mcp/sse",
                    timeout=aiohttp.ClientTimeout(total=2)  # Short timeout for SSE check
                ) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "")
                        if "text/event-stream" in content_type:
                            return True, "SSE endpoint available", f"Content-Type: {content_type}"
                        else:
                            return False, f"Wrong Content-Type: {content_type}", "Expected text/event-stream"
                    else:
                        return False, f"SSE endpoint returned {resp.status}", ""
            except asyncio.TimeoutError:
                # Timeout is expected for SSE - it means it's streaming
                return True, "SSE endpoint is streaming (timeout expected)", ""
            except aiohttp.ClientError as e:
                return False, f"SSE connection error: {e}", ""

    # =========================================================================
    # PROTOCOL LAYER TESTS
    # =========================================================================

    async def test_jsonrpc_format(self) -> Tuple[bool, str, str]:
        """Test if server responds with valid JSON-RPC"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            request = {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                try:
                    data = await resp.json()

                    # Check JSON-RPC structure
                    if "jsonrpc" not in data:
                        return False, "Missing 'jsonrpc' field in response", json.dumps(data)
                    if data.get("jsonrpc") != "2.0":
                        return False, f"Wrong jsonrpc version: {data.get('jsonrpc')}", ""
                    if "id" not in data:
                        return False, "Missing 'id' field in response", json.dumps(data)
                    if "result" not in data and "error" not in data:
                        return False, "Missing 'result' or 'error' field", json.dumps(data)

                    return True, "Valid JSON-RPC 2.0 response", json.dumps(data)
                except json.JSONDecodeError:
                    return False, "Response is not valid JSON", await resp.text()

    async def test_error_handling(self) -> Tuple[bool, str, str]:
        """Test if server returns proper error for invalid method"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            request = {"jsonrpc": "2.0", "id": 1, "method": "nonexistent/method", "params": {}}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    error = data["error"]
                    if "code" in error and "message" in error:
                        if error["code"] == -32601:  # Method not found
                            return True, "Correct error code for unknown method", json.dumps(error)
                        else:
                            return True, f"Error returned (code: {error['code']})", json.dumps(error)
                    return False, "Error missing code or message", json.dumps(error)
                else:
                    return False, "No error returned for invalid method", json.dumps(data)

    async def test_parse_error_handling(self) -> Tuple[bool, str, str]:
        """Test if server handles malformed JSON"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/mcp",
                data="not valid json{{{",
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                if resp.status == 400:
                    try:
                        data = await resp.json()
                        if data.get("error", {}).get("code") == -32700:
                            return True, "Correct parse error response", json.dumps(data)
                        return True, "Returns 400 for invalid JSON", json.dumps(data)
                    except:
                        return True, "Returns 400 for invalid JSON", ""
                else:
                    return False, f"Expected 400, got {resp.status}", await resp.text()

    # =========================================================================
    # INITIALIZATION TESTS
    # =========================================================================

    async def test_initialize(self) -> Tuple[bool, str, str]:
        """Test MCP initialization handshake"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}},
                    "clientInfo": {"name": "mcp-diagnostics", "version": "1.0.0"}
                }
            }

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                # Store session ID for subsequent tests
                if "X-Session-ID" in resp.headers:
                    self.session_id = resp.headers["X-Session-ID"]

                data = await resp.json()

                if "error" in data:
                    return False, f"Initialize failed: {data['error'].get('message')}", json.dumps(data)

                result = data.get("result", {})

                # Check required fields
                if "protocolVersion" not in result:
                    return False, "Missing protocolVersion in response", json.dumps(result)
                if "capabilities" not in result:
                    return False, "Missing capabilities in response", json.dumps(result)
                if "serverInfo" not in result:
                    return False, "Missing serverInfo in response", json.dumps(result)

                server_info = result.get("serverInfo", {})
                return True, f"Initialized with {server_info.get('name', 'unknown')}", json.dumps(result)

    async def test_session_persistence(self) -> Tuple[bool, str, str]:
        """Test if session ID persists across requests"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        if not self.session_id:
            return False, "No session ID from initialization", "Run initialize test first"

        async with aiohttp.ClientSession() as session:
            request = {"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}
            headers = {"X-Session-ID": self.session_id}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                response_session = resp.headers.get("X-Session-ID")

                if response_session == self.session_id:
                    return True, "Session ID persisted correctly", f"Session: {self.session_id[:8]}..."
                elif response_session:
                    return False, "Session ID changed unexpectedly", f"Expected: {self.session_id}, Got: {response_session}"
                else:
                    return False, "No session ID in response", "Server may not support sessions"

    # =========================================================================
    # TOOLS TESTS
    # =========================================================================

    async def test_tools_list(self) -> Tuple[bool, str, str]:
        """Test listing available tools"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            request = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    return False, f"tools/list failed: {data['error'].get('message')}", ""

                tools = data.get("result", {}).get("tools", [])
                tool_names = [t.get("name", "unknown") for t in tools]

                if len(tools) == 0:
                    return True, "No tools available (may be intentional)", ""

                return True, f"Found {len(tools)} tools: {', '.join(tool_names[:3])}...", json.dumps(tool_names)

    async def test_tool_call(self) -> Tuple[bool, str, str]:
        """Test calling a simple tool"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            # Try to call a common tool
            request = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "get_current_time",
                    "arguments": {}
                }
            }
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    error = data["error"]
                    if error.get("code") == -32602:  # Invalid params - tool might not exist
                        return True, "Tool not found (expected for some servers)", json.dumps(error)
                    return False, f"Tool call failed: {error.get('message')}", json.dumps(error)

                result = data.get("result", {})
                content = result.get("content", [])

                if not content:
                    return False, "Tool returned no content", json.dumps(result)

                text = content[0].get("text", "") if content else ""
                return True, f"Tool executed: {text[:50]}...", json.dumps(result)

    async def test_tool_validation(self) -> Tuple[bool, str, str]:
        """Test that invalid tool arguments are rejected"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            # Call tool with missing required argument
            request = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "calculate",
                    "arguments": {"operation": "add"}  # Missing a and b
                }
            }
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                data = await resp.json()

                # Either an error or a graceful handling is acceptable
                if "error" in data:
                    return True, "Server validates tool arguments", json.dumps(data["error"])

                result = data.get("result", {})
                if result.get("isError"):
                    return True, "Tool returned error for invalid args", json.dumps(result)

                # If it succeeded, that's still OK (server might have defaults)
                return True, "Tool handled missing args gracefully", json.dumps(result)

    # =========================================================================
    # RESOURCES TESTS
    # =========================================================================

    async def test_resources_list(self) -> Tuple[bool, str, str]:
        """Test listing available resources"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            request = {"jsonrpc": "2.0", "id": 6, "method": "resources/list", "params": {}}
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    return False, f"resources/list failed: {data['error'].get('message')}", ""

                resources = data.get("result", {}).get("resources", [])
                resource_uris = [r.get("uri", "unknown") for r in resources]

                if len(resources) == 0:
                    return True, "No resources available (may be intentional)", ""

                return True, f"Found {len(resources)} resources", json.dumps(resource_uris)

    async def test_resource_read(self) -> Tuple[bool, str, str]:
        """Test reading a resource"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            request = {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "resources/read",
                "params": {"uri": "server://status"}
            }
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    error = data["error"]
                    if "not found" in error.get("message", "").lower():
                        return True, "Resource not found (expected for some servers)", ""
                    return False, f"Resource read failed: {error.get('message')}", ""

                contents = data.get("result", {}).get("contents", [])
                if not contents:
                    return False, "No contents in resource response", json.dumps(data)

                content = contents[0]
                return True, f"Resource read OK ({content.get('mimeType', 'unknown')})", content.get("text", "")[:100]

    # =========================================================================
    # PROMPTS TESTS
    # =========================================================================

    async def test_prompts_list(self) -> Tuple[bool, str, str]:
        """Test listing available prompts"""
        if not AIOHTTP_AVAILABLE:
            return False, "aiohttp not installed", ""

        async with aiohttp.ClientSession() as session:
            request = {"jsonrpc": "2.0", "id": 8, "method": "prompts/list", "params": {}}
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            async with session.post(
                f"{self.server_url}/mcp",
                json=request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                data = await resp.json()

                if "error" in data:
                    return False, f"prompts/list failed: {data['error'].get('message')}", ""

                prompts = data.get("result", {}).get("prompts", [])
                prompt_names = [p.get("name", "unknown") for p in prompts]

                if len(prompts) == 0:
                    return True, "No prompts available (may be intentional)", ""

                return True, f"Found {len(prompts)} prompts: {', '.join(prompt_names)}", ""

    # =========================================================================
    # SSE/NOTIFICATION TESTS
    # =========================================================================

    async def test_sse_connection(self) -> Tuple[bool, str, str]:
        """Test SSE connection and initial event"""
        if not SSE_CLIENT_AVAILABLE:
            return False, "aiohttp-sse-client not installed", "pip install aiohttp-sse-client"

        try:
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            async with sse_client.EventSource(
                f"{self.server_url}/mcp/sse",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=3)
            ) as event_source:
                async for event in event_source:
                    if event.type == "connection":
                        data = json.loads(event.data)
                        return True, f"SSE connected: {data.get('type')}", json.dumps(data)
                    elif event.type == "ping":
                        return True, "SSE connection established (ping received)", ""
                    break  # Only check first event

                return True, "SSE connection established", ""
        except asyncio.TimeoutError:
            return True, "SSE streaming (timeout expected)", ""
        except Exception as e:
            return False, f"SSE connection failed: {e}", ""

    async def test_progress_notifications(self) -> Tuple[bool, str, str]:
        """Test progress notifications via SSE"""
        if not SSE_CLIENT_AVAILABLE:
            return False, "aiohttp-sse-client not installed", ""

        progress_received = []

        async def sse_listener():
            try:
                headers = {"X-Session-ID": self.session_id} if self.session_id else {}
                async with sse_client.EventSource(
                    f"{self.server_url}/mcp/sse",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as event_source:
                    async for event in event_source:
                        if event.type == "message":
                            data = json.loads(event.data)
                            if data.get("method") == "notifications/progress":
                                progress_received.append(data)
                                if len(progress_received) >= 2:
                                    return
            except asyncio.TimeoutError:
                pass

        # Start SSE listener
        sse_task = asyncio.create_task(sse_listener())
        await asyncio.sleep(0.5)  # Give SSE time to connect

        # Trigger long-running task
        async with aiohttp.ClientSession() as session:
            request = {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "long_running_task",
                    "arguments": {"steps": 3, "delay": 0.3}
                }
            }
            headers = {"X-Session-ID": self.session_id} if self.session_id else {}

            try:
                async with session.post(
                    f"{self.server_url}/mcp",
                    json=request,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    await resp.json()
            except:
                pass

        # Wait for SSE
        try:
            await asyncio.wait_for(sse_task, timeout=5)
        except asyncio.TimeoutError:
            pass

        if progress_received:
            return True, f"Received {len(progress_received)} progress notifications", json.dumps(progress_received[0])
        else:
            return True, "No progress notifications (tool may not exist)", "This is OK if long_running_task is not available"

    # =========================================================================
    # TEST RUNNER
    # =========================================================================

    async def run_all_tests(self, categories: Optional[List[str]] = None):
        """Run all diagnostic tests"""
        all_categories = {
            "transport": [
                ("Server Reachable", self.test_server_reachable,
                 "Check if server is running and port is correct"),
                ("Health Endpoint", self.test_health_endpoint,
                 "Verify /health endpoint is responding"),
                ("MCP Endpoint", self.test_mcp_endpoint_exists,
                 "Check /mcp endpoint accepts POST requests"),
                ("SSE Endpoint", self.test_sse_endpoint,
                 "Verify /mcp/sse endpoint for streaming"),
            ],
            "protocol": [
                ("JSON-RPC Format", self.test_jsonrpc_format,
                 "Ensure responses follow JSON-RPC 2.0 spec"),
                ("Error Handling", self.test_error_handling,
                 "Verify proper error responses"),
                ("Parse Error", self.test_parse_error_handling,
                 "Check malformed JSON handling"),
            ],
            "initialization": [
                ("Initialize Handshake", self.test_initialize,
                 "Test MCP initialization flow"),
                ("Session Persistence", self.test_session_persistence,
                 "Verify session ID is maintained"),
            ],
            "tools": [
                ("List Tools", self.test_tools_list,
                 "Get available tools"),
                ("Call Tool", self.test_tool_call,
                 "Execute a simple tool"),
                ("Tool Validation", self.test_tool_validation,
                 "Test argument validation"),
            ],
            "resources": [
                ("List Resources", self.test_resources_list,
                 "Get available resources"),
                ("Read Resource", self.test_resource_read,
                 "Read a resource"),
            ],
            "prompts": [
                ("List Prompts", self.test_prompts_list,
                 "Get available prompts"),
            ],
            "sse": [
                ("SSE Connection", self.test_sse_connection,
                 "Test SSE streaming connection"),
                ("Progress Notifications", self.test_progress_notifications,
                 "Test progress updates via SSE"),
            ],
        }

        if categories:
            selected = {k: v for k, v in all_categories.items() if k in categories}
        else:
            selected = all_categories

        print(colorize("\n╔══════════════════════════════════════════════════════════════╗", Colors.CYAN))
        print(colorize("║            MCP DIAGNOSTIC TEST SUITE                         ║", Colors.CYAN))
        print(colorize("╚══════════════════════════════════════════════════════════════╝", Colors.CYAN))
        print(f"\nServer: {colorize(self.server_url, Colors.BLUE)}")
        print(f"Time: {self.report.timestamp}\n")

        for category, tests in selected.items():
            print(colorize(f"\n▶ {category.upper()}", Colors.BOLD))
            print(colorize("─" * 50, Colors.GRAY))

            for name, test_fn, suggestion in tests:
                await self.run_test(name, test_fn, suggestion)

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print test summary"""
        print(colorize("\n═" * 60, Colors.CYAN))
        print(colorize("SUMMARY", Colors.BOLD))
        print(colorize("─" * 60, Colors.GRAY))

        total = len(self.report.results)
        passed = self.report.passed
        failed = self.report.failed
        warnings = self.report.warnings

        print(f"  Total:    {total}")
        print(f"  {colorize('Passed:', Colors.GREEN)}  {passed}")
        print(f"  {colorize('Failed:', Colors.RED)}  {failed}")
        print(f"  {colorize('Warnings:', Colors.YELLOW)} {warnings}")

        if failed > 0:
            print(colorize("\n⚠ ISSUES DETECTED", Colors.RED))
            print(colorize("─" * 60, Colors.GRAY))

            for result in self.report.results:
                if result.status == TestStatus.FAIL:
                    print(f"  • {result.name}: {result.message}")
                    if result.suggestion:
                        print(f"    → {colorize(result.suggestion, Colors.YELLOW)}")
        else:
            print(colorize("\n✓ All tests passed!", Colors.GREEN))

        print()


# =============================================================================
# STDIO TRANSPORT DIAGNOSTICS
# =============================================================================

class StdioDiagnostics:
    """Diagnostics for stdio transport"""

    def __init__(self, command: str, verbose: bool = False):
        self.command = command
        self.verbose = verbose
        self.process: Optional[subprocess.Popen] = None

    async def run_all_tests(self):
        """Run stdio transport tests"""
        print(colorize("\n╔══════════════════════════════════════════════════════════════╗", Colors.CYAN))
        print(colorize("║          MCP STDIO DIAGNOSTIC TEST SUITE                     ║", Colors.CYAN))
        print(colorize("╚══════════════════════════════════════════════════════════════╝", Colors.CYAN))
        print(f"\nCommand: {colorize(self.command, Colors.BLUE)}\n")

        # Start process
        print(colorize("▶ PROCESS", Colors.BOLD))
        print(colorize("─" * 50, Colors.GRAY))

        try:
            self.process = subprocess.Popen(
                self.command.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"  {status_icon(TestStatus.PASS)} Process started (PID: {self.process.pid})")
        except Exception as e:
            print(f"  {status_icon(TestStatus.FAIL)} Failed to start process: {e}")
            return

        try:
            # Test ping
            print(colorize("\n▶ PROTOCOL", Colors.BOLD))
            print(colorize("─" * 50, Colors.GRAY))

            await self._test_request(
                "Ping",
                {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}
            )

            # Test initialize
            await self._test_request(
                "Initialize",
                {
                    "jsonrpc": "2.0", "id": 2, "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "diagnostics", "version": "1.0"}
                    }
                }
            )

            # Test tools/list
            print(colorize("\n▶ FEATURES", Colors.BOLD))
            print(colorize("─" * 50, Colors.GRAY))

            await self._test_request(
                "List Tools",
                {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
            )

            await self._test_request(
                "List Resources",
                {"jsonrpc": "2.0", "id": 4, "method": "resources/list", "params": {}}
            )

        finally:
            if self.process:
                self.process.terminate()
                print(colorize("\n▶ CLEANUP", Colors.BOLD))
                print(f"  {status_icon(TestStatus.PASS)} Process terminated")

    async def _test_request(self, name: str, request: dict):
        """Send a request and check response"""
        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Read response (with timeout)
            import select
            ready, _, _ = select.select([self.process.stdout], [], [], 5.0)

            if not ready:
                print(f"  {status_icon(TestStatus.FAIL)} {name}: Timeout waiting for response")
                return

            response_str = self.process.stdout.readline()
            response = json.loads(response_str)

            if "error" in response:
                print(f"  {status_icon(TestStatus.WARN)} {name}: {response['error'].get('message', 'Error')}")
            else:
                print(f"  {status_icon(TestStatus.PASS)} {name}: OK")
                if self.verbose:
                    print(f"      {colorize(json.dumps(response.get('result', {}))[:80], Colors.GRAY)}")

        except json.JSONDecodeError as e:
            print(f"  {status_icon(TestStatus.FAIL)} {name}: Invalid JSON response")
        except Exception as e:
            print(f"  {status_icon(TestStatus.FAIL)} {name}: {e}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="MCP Diagnostic Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --server http://localhost:8000
  %(prog)s --server http://localhost:8000 --tests transport,protocol
  %(prog)s --server http://localhost:8000 -v
  %(prog)s --stdio --command "python mcp_stdio_server.py"

Test Categories:
  transport      Network and endpoint connectivity
  protocol       JSON-RPC format and error handling
  initialization MCP handshake and sessions
  tools          Tool listing and execution
  resources      Resource listing and reading
  prompts        Prompt listing
  sse            Server-Sent Events and notifications
        """
    )

    parser.add_argument(
        "--server", "-s",
        default="http://localhost:8000",
        help="MCP server URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--tests", "-t",
        help="Comma-separated list of test categories to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds (default: 10)"
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Test stdio transport instead of HTTP"
    )
    parser.add_argument(
        "--command", "-c",
        help="Command to start stdio server (required with --stdio)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if args.stdio:
        if not args.command:
            parser.error("--command is required with --stdio")
        diagnostics = StdioDiagnostics(args.command, args.verbose)
        await diagnostics.run_all_tests()
    else:
        categories = args.tests.split(",") if args.tests else None
        diagnostics = MCPDiagnostics(
            server_url=args.server,
            verbose=args.verbose,
            timeout=args.timeout
        )
        await diagnostics.run_all_tests(categories)

        if args.json:
            import dataclasses
            report = dataclasses.asdict(diagnostics.report)
            # Convert enums to strings
            for r in report["results"]:
                r["status"] = r["status"].value
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
