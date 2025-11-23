"""
Unit tests for MCP Server

Run with: pytest tests/ -v
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import MCPServer, MCPSession, PROTOCOL_VERSION


class TestMCPServer:
    """Tests for MCPServer class"""

    @pytest.fixture
    def server(self):
        """Create a server instance for testing"""
        return MCPServer(name="test-server", version="1.0.0")

    @pytest.fixture
    def session(self):
        """Create a session for testing"""
        return MCPSession(session_id="test-session-123")

    # === Initialization Tests ===

    def test_server_creation(self, server):
        """Test server initializes correctly"""
        assert server.name == "test-server"
        assert server.version == "1.0.0"
        assert "tools" in server.capabilities
        assert "resources" in server.capabilities

    def test_server_has_default_tools(self, server):
        """Test server has built-in tools"""
        assert "get_current_time" in server._tools
        assert "calculate" in server._tools
        assert "add_note" in server._tools

    def test_server_has_default_resources(self, server):
        """Test server has built-in resources"""
        assert "server://status" in server._resources
        assert "server://counter" in server._resources

    # === Protocol Tests ===

    @pytest.mark.asyncio
    async def test_initialize_handler(self, server, session):
        """Test initialize method returns correct structure"""
        params = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }

        result = await server._handle_initialize(params, session)

        assert "protocolVersion" in result
        assert result["protocolVersion"] == PROTOCOL_VERSION
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "test-server"

    @pytest.mark.asyncio
    async def test_ping_handler(self, server, session):
        """Test ping returns empty dict"""
        result = await server._handle_ping({}, session)
        assert result == {}

    @pytest.mark.asyncio
    async def test_initialized_handler(self, server, session):
        """Test initialized notification sets session state"""
        assert not session.initialized
        result = await server._handle_initialized({}, session)
        assert session.initialized
        assert result is None  # Notifications return None

    # === Tools Tests ===

    @pytest.mark.asyncio
    async def test_tools_list(self, server, session):
        """Test tools/list returns all tools"""
        result = await server._handle_tools_list({}, session)

        assert "tools" in result
        tools = result["tools"]
        assert len(tools) > 0

        # Check tool structure
        tool = tools[0]
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool

    @pytest.mark.asyncio
    async def test_tool_call_get_time(self, server, session):
        """Test calling get_current_time tool"""
        result = await server._handle_tools_call(
            {"name": "get_current_time", "arguments": {}},
            session
        )

        assert "content" in result
        assert len(result["content"]) > 0
        assert "text" in result["content"][0]
        assert "Current time" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_tool_call_calculate_add(self, server, session):
        """Test calculate tool with addition"""
        result = await server._handle_tools_call(
            {"name": "calculate", "arguments": {"operation": "add", "a": 5, "b": 3}},
            session
        )

        assert "content" in result
        text = result["content"][0]["text"]
        assert "8" in text

    @pytest.mark.asyncio
    async def test_tool_call_calculate_divide(self, server, session):
        """Test calculate tool with division"""
        result = await server._handle_tools_call(
            {"name": "calculate", "arguments": {"operation": "divide", "a": 10, "b": 2}},
            session
        )

        assert "content" in result
        text = result["content"][0]["text"]
        assert "5" in text

    @pytest.mark.asyncio
    async def test_tool_call_divide_by_zero(self, server, session):
        """Test calculate tool handles division by zero"""
        result = await server._handle_tools_call(
            {"name": "calculate", "arguments": {"operation": "divide", "a": 10, "b": 0}},
            session
        )

        assert "isError" in result
        assert result["isError"] is True

    @pytest.mark.asyncio
    async def test_tool_call_unknown_tool(self, server, session):
        """Test calling unknown tool raises error"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await server._handle_tools_call(
                {"name": "nonexistent_tool", "arguments": {}},
                session
            )

    @pytest.mark.asyncio
    async def test_tool_increment_counter(self, server, session):
        """Test increment_counter tool"""
        initial = server.counter

        result = await server._handle_tools_call(
            {"name": "increment_counter", "arguments": {"amount": 5}},
            session
        )

        assert server.counter == initial + 5
        assert "content" in result

    @pytest.mark.asyncio
    async def test_tool_add_note(self, server, session):
        """Test add_note tool"""
        initial_count = len(server.notes)

        result = await server._handle_tools_call(
            {"name": "add_note", "arguments": {"content": "Test note", "tags": ["test"]}},
            session
        )

        assert len(server.notes) == initial_count + 1
        assert server.notes[-1]["content"] == "Test note"
        assert "test" in server.notes[-1]["tags"]

    @pytest.mark.asyncio
    async def test_tool_get_notes(self, server, session):
        """Test get_notes tool"""
        # Add some notes first
        server.notes.append({"id": 1, "content": "Note 1", "tags": []})
        server.notes.append({"id": 2, "content": "Note 2", "tags": ["important"]})

        result = await server._handle_tools_call(
            {"name": "get_notes", "arguments": {"limit": 10}},
            session
        )

        assert "content" in result
        text = result["content"][0]["text"]
        assert "Note 1" in text or "Note 2" in text

    # === Resources Tests ===

    @pytest.mark.asyncio
    async def test_resources_list(self, server, session):
        """Test resources/list returns all resources"""
        result = await server._handle_resources_list({}, session)

        assert "resources" in result
        resources = result["resources"]
        assert len(resources) > 0

        # Check resource structure
        resource = resources[0]
        assert "uri" in resource
        assert "name" in resource
        assert "mimeType" in resource

    @pytest.mark.asyncio
    async def test_resource_read_status(self, server, session):
        """Test reading server status resource"""
        result = await server._handle_resources_read(
            {"uri": "server://status"},
            session
        )

        assert "contents" in result
        assert len(result["contents"]) > 0
        content = result["contents"][0]
        assert content["uri"] == "server://status"
        assert content["mimeType"] == "application/json"

        # Parse and check status
        status = json.loads(content["text"])
        assert "status" in status
        assert status["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_resource_read_counter(self, server, session):
        """Test reading counter resource"""
        server.counter = 42

        result = await server._handle_resources_read(
            {"uri": "server://counter"},
            session
        )

        assert "contents" in result
        content = result["contents"][0]
        assert content["text"] == "42"

    @pytest.mark.asyncio
    async def test_resource_read_unknown(self, server, session):
        """Test reading unknown resource raises error"""
        with pytest.raises(ValueError, match="Resource not found"):
            await server._handle_resources_read(
                {"uri": "unknown://resource"},
                session
            )

    # === Subscription Tests ===

    @pytest.mark.asyncio
    async def test_resource_subscribe(self, server, session):
        """Test subscribing to a resource"""
        await server._handle_resources_subscribe(
            {"uri": "server://counter"},
            session
        )

        assert "server://counter" in session.subscribed_resources

    @pytest.mark.asyncio
    async def test_resource_unsubscribe(self, server, session):
        """Test unsubscribing from a resource"""
        session.subscribed_resources.add("server://counter")

        await server._handle_resources_unsubscribe(
            {"uri": "server://counter"},
            session
        )

        assert "server://counter" not in session.subscribed_resources

    # === Prompts Tests ===

    @pytest.mark.asyncio
    async def test_prompts_list(self, server, session):
        """Test prompts/list returns all prompts"""
        result = await server._handle_prompts_list({}, session)

        assert "prompts" in result
        prompts = result["prompts"]
        assert len(prompts) > 0

    @pytest.mark.asyncio
    async def test_prompt_get_greeting(self, server, session):
        """Test getting greeting prompt"""
        result = await server._handle_prompts_get(
            {"name": "greeting", "arguments": {"name": "Alice", "style": "formal"}},
            session
        )

        assert "messages" in result
        messages = result["messages"]
        assert len(messages) > 0
        assert "Alice" in messages[0]["content"]["text"]

    # === Request Handler Tests ===

    @pytest.mark.asyncio
    async def test_handle_request_success(self, server, session):
        """Test full request handling"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "ping",
            "params": {}
        }

        response = await server.handle_request(request, session)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response

    @pytest.mark.asyncio
    async def test_handle_request_method_not_found(self, server, session):
        """Test handling unknown method"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {}
        }

        response = await server.handle_request(request, session)

        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_handle_notification(self, server, session):
        """Test handling notification (no id)"""
        request = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }

        response = await server.handle_request(request, session)
        assert response is None  # Notifications don't return responses


class TestMCPSession:
    """Tests for MCPSession class"""

    def test_session_creation(self):
        """Test session initializes correctly"""
        session = MCPSession(session_id="test-123")

        assert session.session_id == "test-123"
        assert not session.initialized
        assert len(session.subscribed_resources) == 0
        assert session.sse_queue is None

    def test_session_subscriptions(self):
        """Test session subscription management"""
        session = MCPSession(session_id="test-123")

        session.subscribed_resources.add("server://counter")
        assert "server://counter" in session.subscribed_resources

        session.subscribed_resources.discard("server://counter")
        assert "server://counter" not in session.subscribed_resources


# === Integration-style Tests ===

class TestServerIntegration:
    """Integration tests that test multiple components together"""

    @pytest.fixture
    def server(self):
        return MCPServer()

    @pytest.fixture
    def session(self):
        return MCPSession(session_id="integration-test")

    @pytest.mark.asyncio
    async def test_full_workflow(self, server, session):
        """Test a complete MCP workflow"""
        # 1. Initialize
        init_result = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test"}
            }
        }, session)
        assert "result" in init_result

        # 2. Send initialized notification
        await server.handle_request({
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }, session)
        assert session.initialized

        # 3. List tools
        tools_result = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }, session)
        assert "result" in tools_result

        # 4. Call a tool
        call_result = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_current_time", "arguments": {}}
        }, session)
        assert "result" in call_result

        # 5. Read a resource
        read_result = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {"uri": "server://status"}
        }, session)
        assert "result" in read_result

    @pytest.mark.asyncio
    async def test_note_workflow(self, server, session):
        """Test adding and retrieving notes"""
        # Add a note
        add_result = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "add_note",
                "arguments": {"content": "Test note", "tags": ["test"]}
            }
        }, session)
        assert "result" in add_result

        # Get notes
        get_result = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_notes",
                "arguments": {"tags": ["test"]}
            }
        }, session)
        assert "result" in get_result
        assert "Test note" in get_result["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_counter_workflow(self, server, session):
        """Test counter increment and resource read"""
        initial_counter = server.counter

        # Increment
        await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "increment_counter",
                "arguments": {"amount": 10}
            }
        }, session)

        # Read counter resource
        read_result = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/read",
            "params": {"uri": "server://counter"}
        }, session)

        counter_value = int(read_result["result"]["contents"][0]["text"])
        assert counter_value == initial_counter + 10
