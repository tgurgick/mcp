#!/usr/bin/env python3
"""
MCP Server with Full Observability

Features:
- OpenTelemetry tracing (Jaeger, OTLP, Console exporters)
- Prometheus metrics
- Structured JSON logging with trace correlation
- Request validation with Pydantic
- Graceful shutdown
- Configuration management
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field

from aiohttp import web
from aiohttp_sse import sse_response
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Optional exporters (graceful fallback if not installed)
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False

try:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from prometheus_client import start_http_server as start_prometheus_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Server configuration from environment variables"""

    # Server settings
    HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("MCP_PORT", "8000"))
    SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "mcp-server")
    SERVER_VERSION: str = os.getenv("MCP_SERVER_VERSION", "1.0.0")

    # Observability settings
    OTEL_ENABLED: bool = os.getenv("OTEL_ENABLED", "true").lower() == "true"
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "mcp-server")
    OTEL_EXPORTER: str = os.getenv("OTEL_EXPORTER", "console")  # console, otlp, jaeger
    OTLP_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    # Metrics settings
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # json or text

    # Protocol
    PROTOCOL_VERSION: str = "2024-11-05"


# =============================================================================
# Structured Logging with Trace Correlation
# =============================================================================

class JSONFormatter(logging.Formatter):
    """JSON log formatter with OpenTelemetry trace correlation"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace context if available
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            log_data["trace_id"] = format(ctx.trace_id, "032x")
            log_data["span_id"] = format(ctx.span_id, "016x")

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(config: Config) -> logging.Logger:
    """Configure structured logging"""
    logger = logging.getLogger("mcp")
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))

    handler = logging.StreamHandler()

    if config.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    logger.addHandler(handler)
    return logger


class TracingLogger:
    """Logger wrapper that adds trace context and structured fields"""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log(self, level: int, msg: str, **kwargs):
        record = self._logger.makeRecord(
            self._logger.name, level, "", 0, msg, (), None
        )
        record.extra_fields = kwargs
        self._logger.handle(record)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)


# =============================================================================
# OpenTelemetry Setup
# =============================================================================

def setup_tracing(config: Config) -> trace.Tracer:
    """Configure OpenTelemetry tracing"""

    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: config.OTEL_SERVICE_NAME,
        ResourceAttributes.SERVICE_VERSION: config.SERVER_VERSION,
    })

    provider = TracerProvider(resource=resource)

    # Configure exporter based on config
    if config.OTEL_EXPORTER == "console":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    elif config.OTEL_EXPORTER == "otlp" and OTLP_AVAILABLE:
        provider.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(endpoint=config.OTLP_ENDPOINT)
        ))

    trace.set_tracer_provider(provider)
    return trace.get_tracer(config.OTEL_SERVICE_NAME)


def setup_metrics(config: Config):
    """Configure OpenTelemetry metrics"""

    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: config.OTEL_SERVICE_NAME,
    })

    readers = []

    # Prometheus exporter
    if PROMETHEUS_AVAILABLE:
        readers.append(PrometheusMetricReader())
        start_prometheus_server(config.METRICS_PORT)
    else:
        # Fallback to console
        readers.append(PeriodicExportingMetricReader(
            ConsoleMetricExporter(),
            export_interval_millis=60000
        ))

    provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(provider)

    return metrics.get_meter(config.OTEL_SERVICE_NAME)


# =============================================================================
# Pydantic Request/Response Models
# =============================================================================

class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 Request"""
    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    id: Optional[Union[str, int]] = None
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 Error"""
    code: int
    message: str
    data: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 Response"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JsonRpcError] = None


class ToolCallParams(BaseModel):
    """Parameters for tools/call"""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ResourceReadParams(BaseModel):
    """Parameters for resources/read"""
    uri: str


class PromptGetParams(BaseModel):
    """Parameters for prompts/get"""
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# MCP Session
# =============================================================================

@dataclass
class MCPSession:
    """Represents an MCP client session"""
    session_id: str
    client_info: Dict[str, Any] = field(default_factory=dict)
    client_capabilities: Dict[str, Any] = field(default_factory=dict)
    initialized: bool = False
    subscribed_resources: Set[str] = field(default_factory=set)
    sse_queue: Optional[asyncio.Queue] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)


# =============================================================================
# MCP Server with Observability
# =============================================================================

class MCPServer:
    """MCP Server with full observability"""

    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, MCPSession] = {}

        # Server state
        self.counter = 0
        self.notes: List[Dict[str, Any]] = []

        # Setup observability
        self.logger = TracingLogger(setup_logging(config))
        self.tracer = setup_tracing(config) if config.OTEL_ENABLED else None

        if config.METRICS_ENABLED:
            self.meter = setup_metrics(config)
            self._setup_metrics()
        else:
            self.meter = None

        # Server capabilities
        self.capabilities = {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True},
            "logging": {}
        }

        # Initialize components
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._resource_templates: List[Dict[str, Any]] = []
        self._prompts: Dict[str, Dict[str, Any]] = {}

        self._register_builtin_tools()
        self._register_builtin_resources()
        self._register_builtin_prompts()

        # Request handlers
        self._handlers: Dict[str, Callable] = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "ping": self._handle_ping,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "resources/subscribe": self._handle_resources_subscribe,
            "resources/unsubscribe": self._handle_resources_unsubscribe,
            "resources/templates/list": self._handle_resource_templates_list,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
            "logging/setLevel": self._handle_logging_set_level,
            "completion/complete": self._handle_completion,
        }

        self.logger.info("MCP Server initialized",
                        server_name=config.SERVER_NAME,
                        version=config.SERVER_VERSION,
                        otel_enabled=config.OTEL_ENABLED)

    def _setup_metrics(self):
        """Setup Prometheus/OTEL metrics"""
        self.request_counter = self.meter.create_counter(
            "mcp_requests_total",
            description="Total MCP requests",
            unit="1"
        )

        self.request_duration = self.meter.create_histogram(
            "mcp_request_duration_seconds",
            description="MCP request duration",
            unit="s"
        )

        self.active_sessions = self.meter.create_up_down_counter(
            "mcp_active_sessions",
            description="Number of active sessions",
            unit="1"
        )

        self.tool_calls = self.meter.create_counter(
            "mcp_tool_calls_total",
            description="Total tool calls",
            unit="1"
        )

        self.errors_counter = self.meter.create_counter(
            "mcp_errors_total",
            description="Total errors",
            unit="1"
        )

    @asynccontextmanager
    async def _trace_request(self, method: str, session_id: str):
        """Context manager for tracing requests"""
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            f"mcp.{method}",
            kind=SpanKind.SERVER
        ) as span:
            span.set_attribute("mcp.method", method)
            span.set_attribute("mcp.session_id", session_id)
            span.set_attribute("mcp.protocol_version", self.config.PROTOCOL_VERSION)

            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def _register_builtin_tools(self):
        """Register built-in tools"""
        self._tools = {
            "get_current_time": {
                "name": "get_current_time",
                "description": "Returns the current server time in ISO 8601 format",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "Optional timezone",
                            "default": "UTC"
                        }
                    },
                    "required": []
                }
            },
            "increment_counter": {
                "name": "increment_counter",
                "description": "Increments the server counter",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "integer",
                            "description": "Amount to increment",
                            "default": 1
                        }
                    },
                    "required": []
                }
            },
            "add_note": {
                "name": "add_note",
                "description": "Adds a note to the collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Note content"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": []
                        }
                    },
                    "required": ["content"]
                }
            },
            "get_notes": {
                "name": "get_notes",
                "description": "Retrieves notes",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 10},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": []
                }
            },
            "calculate": {
                "name": "calculate",
                "description": "Performs arithmetic calculations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["add", "subtract", "multiply", "divide"]
                        },
                        "a": {"type": "number"},
                        "b": {"type": "number"}
                    },
                    "required": ["operation", "a", "b"]
                }
            },
            "long_running_task": {
                "name": "long_running_task",
                "description": "Simulates a long-running task with progress",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "steps": {"type": "integer", "default": 5},
                        "delay": {"type": "number", "default": 0.5}
                    },
                    "required": []
                }
            }
        }

    def _register_builtin_resources(self):
        """Register built-in resources"""
        self._resources = {
            "server://status": {
                "uri": "server://status",
                "name": "Server Status",
                "description": "Server health and status",
                "mimeType": "application/json"
            },
            "server://notes": {
                "uri": "server://notes",
                "name": "All Notes",
                "description": "All stored notes",
                "mimeType": "application/json"
            },
            "server://counter": {
                "uri": "server://counter",
                "name": "Counter",
                "description": "Current counter value",
                "mimeType": "text/plain"
            },
            "server://metrics": {
                "uri": "server://metrics",
                "name": "Server Metrics",
                "description": "Server performance metrics",
                "mimeType": "application/json"
            }
        }

        self._resource_templates = [
            {
                "uriTemplate": "note://{id}",
                "name": "Individual Note",
                "description": "Access a specific note",
                "mimeType": "application/json"
            }
        ]

    def _register_builtin_prompts(self):
        """Register built-in prompts"""
        self._prompts = {
            "greeting": {
                "name": "greeting",
                "description": "A customizable greeting",
                "arguments": [
                    {"name": "name", "required": True},
                    {"name": "style", "required": False}
                ]
            },
            "summarize_notes": {
                "name": "summarize_notes",
                "description": "Summarize stored notes",
                "arguments": [
                    {"name": "max_notes", "required": False}
                ]
            }
        }

    # === Request Handlers ===

    async def _handle_initialize(self, params: Dict, session: MCPSession) -> Dict:
        """Handle initialize"""
        session.client_info = params.get("clientInfo", {})
        session.client_capabilities = params.get("capabilities", {})

        self.logger.info("Client initializing",
                        client_name=session.client_info.get("name"),
                        session_id=session.session_id)

        if self.meter:
            self.active_sessions.add(1)

        return {
            "protocolVersion": self.config.PROTOCOL_VERSION,
            "capabilities": self.capabilities,
            "serverInfo": {
                "name": self.config.SERVER_NAME,
                "version": self.config.SERVER_VERSION
            }
        }

    async def _handle_initialized(self, params: Dict, session: MCPSession) -> None:
        """Handle initialized notification"""
        session.initialized = True
        self.logger.info("Session initialized", session_id=session.session_id)
        return None

    async def _handle_ping(self, params: Dict, session: MCPSession) -> Dict:
        """Handle ping"""
        return {}

    async def _handle_tools_list(self, params: Dict, session: MCPSession) -> Dict:
        """Handle tools/list"""
        return {"tools": list(self._tools.values())}

    async def _handle_tools_call(self, params: Dict, session: MCPSession) -> Dict:
        """Handle tools/call"""
        # Validate params
        try:
            validated = ToolCallParams(**params)
        except ValidationError as e:
            raise ValueError(f"Invalid parameters: {e}")

        tool_name = validated.name
        arguments = validated.arguments

        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Record metric
        if self.meter:
            self.tool_calls.add(1, {"tool": tool_name})

        # Create child span for tool execution
        if self.tracer:
            with self.tracer.start_as_current_span(f"tool.{tool_name}") as span:
                span.set_attribute("tool.name", tool_name)
                span.set_attribute("tool.arguments", json.dumps(arguments))
                result = await self._execute_tool(tool_name, arguments, session)
                return result
        else:
            return await self._execute_tool(tool_name, arguments, session)

    async def _execute_tool(self, name: str, arguments: Dict, session: MCPSession) -> Dict:
        """Execute a tool"""
        self.logger.debug("Executing tool", tool=name, arguments=arguments)

        if name == "get_current_time":
            current_time = datetime.utcnow().isoformat() + "Z"
            return {"content": [{"type": "text", "text": f"Current time: {current_time}"}]}

        elif name == "increment_counter":
            amount = arguments.get("amount", 1)
            old_value = self.counter
            self.counter += amount
            await self._notify_resource_changed("server://counter", session)
            return {"content": [{"type": "text", "text": f"Counter: {old_value} -> {self.counter}"}]}

        elif name == "add_note":
            note = {
                "id": len(self.notes) + 1,
                "content": arguments.get("content", ""),
                "tags": arguments.get("tags", []),
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            self.notes.append(note)
            await self._notify_resource_changed("server://notes", session)
            return {"content": [{"type": "text", "text": f"Note added: ID {note['id']}"}]}

        elif name == "get_notes":
            limit = arguments.get("limit", 10)
            filter_tags = arguments.get("tags", [])
            filtered = self.notes
            if filter_tags:
                filtered = [n for n in self.notes if any(t in n.get("tags", []) for t in filter_tags)]
            result_notes = filtered[-limit:] if limit else filtered
            return {"content": [{"type": "text", "text": json.dumps(result_notes, indent=2)}]}

        elif name == "calculate":
            op = arguments.get("operation")
            a, b = arguments.get("a", 0), arguments.get("b", 0)

            if op == "add": result = a + b
            elif op == "subtract": result = a - b
            elif op == "multiply": result = a * b
            elif op == "divide":
                if b == 0:
                    return {"content": [{"type": "text", "text": "Error: Division by zero"}], "isError": True}
                result = a / b
            else:
                return {"content": [{"type": "text", "text": f"Unknown operation: {op}"}], "isError": True}

            return {"content": [{"type": "text", "text": f"{a} {op} {b} = {result}"}]}

        elif name == "long_running_task":
            steps = arguments.get("steps", 5)
            delay = arguments.get("delay", 0.5)

            for i in range(steps):
                await asyncio.sleep(delay)
                await self._send_progress(session, i + 1, steps, f"Step {i + 1}")

            return {"content": [{"type": "text", "text": f"Completed {steps} steps"}]}

        return {"content": [{"type": "text", "text": f"Tool not implemented: {name}"}], "isError": True}

    async def _handle_resources_list(self, params: Dict, session: MCPSession) -> Dict:
        return {"resources": list(self._resources.values())}

    async def _handle_resources_read(self, params: Dict, session: MCPSession) -> Dict:
        try:
            validated = ResourceReadParams(**params)
        except ValidationError as e:
            raise ValueError(f"Invalid parameters: {e}")

        uri = validated.uri

        if uri == "server://status":
            status = {
                "status": "healthy",
                "server": self.config.SERVER_NAME,
                "version": self.config.SERVER_VERSION,
                "protocol_version": self.config.PROTOCOL_VERSION,
                "active_sessions": len(self.sessions),
                "notes_count": len(self.notes),
                "counter": self.counter,
                "uptime_seconds": time.time() - min(s.created_at for s in self.sessions.values()) if self.sessions else 0
            }
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(status, indent=2)}]}

        elif uri == "server://notes":
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(self.notes, indent=2)}]}

        elif uri == "server://counter":
            return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": str(self.counter)}]}

        elif uri == "server://metrics":
            metrics_data = {
                "sessions": len(self.sessions),
                "notes": len(self.notes),
                "counter": self.counter,
                "tools": len(self._tools),
                "resources": len(self._resources)
            }
            return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(metrics_data, indent=2)}]}

        elif uri.startswith("note://"):
            note_id = int(uri.replace("note://", ""))
            note = next((n for n in self.notes if n["id"] == note_id), None)
            if note:
                return {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(note, indent=2)}]}
            raise ValueError(f"Note not found: {note_id}")

        raise ValueError(f"Resource not found: {uri}")

    async def _handle_resources_subscribe(self, params: Dict, session: MCPSession) -> Dict:
        uri = params.get("uri", "")
        session.subscribed_resources.add(uri)
        self.logger.info("Resource subscribed", uri=uri, session_id=session.session_id)
        return {}

    async def _handle_resources_unsubscribe(self, params: Dict, session: MCPSession) -> Dict:
        uri = params.get("uri", "")
        session.subscribed_resources.discard(uri)
        return {}

    async def _handle_resource_templates_list(self, params: Dict, session: MCPSession) -> Dict:
        return {"resourceTemplates": self._resource_templates}

    async def _handle_prompts_list(self, params: Dict, session: MCPSession) -> Dict:
        return {"prompts": list(self._prompts.values())}

    async def _handle_prompts_get(self, params: Dict, session: MCPSession) -> Dict:
        try:
            validated = PromptGetParams(**params)
        except ValidationError as e:
            raise ValueError(f"Invalid parameters: {e}")

        name = validated.name
        arguments = validated.arguments

        if name == "greeting":
            person_name = arguments.get("name", "User")
            style = arguments.get("style", "casual")

            if style == "formal":
                text = f"Good day, {person_name}. How may I assist you?"
            elif style == "enthusiastic":
                text = f"Hey {person_name}! Great to see you!"
            else:
                text = f"Hello, {person_name}!"

            return {"messages": [{"role": "user", "content": {"type": "text", "text": text}}]}

        elif name == "summarize_notes":
            max_notes = int(arguments.get("max_notes", 10))
            recent = self.notes[-max_notes:]
            notes_text = "\n".join([f"- {n['content']}" for n in recent]) or "No notes."
            return {"messages": [{"role": "user", "content": {"type": "text", "text": f"Summarize:\n{notes_text}"}}]}

        raise ValueError(f"Prompt not found: {name}")

    async def _handle_logging_set_level(self, params: Dict, session: MCPSession) -> Dict:
        level = params.get("level", "info").upper()
        logging.getLogger("mcp").setLevel(getattr(logging, level, logging.INFO))
        return {}

    async def _handle_completion(self, params: Dict, session: MCPSession) -> Dict:
        ref = params.get("ref", {})
        argument = params.get("argument", {})

        completions = []
        if ref.get("type") == "ref/prompt" and ref.get("name") == "greeting":
            if argument.get("name") == "style":
                completions = ["formal", "casual", "enthusiastic"]

        return {"completion": {"values": completions, "hasMore": False}}

    # === Notification Helpers ===

    async def _send_progress(self, session: MCPSession, progress: int, total: int, message: str):
        if session.sse_queue:
            await session.sse_queue.put({
                "jsonrpc": "2.0",
                "method": "notifications/progress",
                "params": {"progress": progress, "total": total, "message": message}
            })

    async def _notify_resource_changed(self, uri: str, source_session: MCPSession):
        for session in self.sessions.values():
            if uri in session.subscribed_resources and session.sse_queue:
                await session.sse_queue.put({
                    "jsonrpc": "2.0",
                    "method": "notifications/resources/updated",
                    "params": {"uri": uri}
                })

    # === Main Request Handler ===

    async def handle_request(self, request: Dict, session: MCPSession) -> Optional[Dict]:
        """Process JSON-RPC request with tracing"""
        start_time = time.time()
        method = request.get("method", "unknown")
        request_id = request.get("id")

        async with self._trace_request(method, session.session_id):
            # Record metric
            if self.meter:
                self.request_counter.add(1, {"method": method})

            # Validate request
            try:
                validated = JsonRpcRequest(**request)
            except ValidationError as e:
                self.logger.error("Invalid request", error=str(e))
                if self.meter:
                    self.errors_counter.add(1, {"type": "validation"})
                return JsonRpcResponse(
                    id=request_id,
                    error=JsonRpcError(code=-32600, message=f"Invalid request: {e}")
                ).model_dump(exclude_none=True)

            handler = self._handlers.get(validated.method)
            if not handler:
                self.logger.warning("Method not found", method=validated.method)
                if self.meter:
                    self.errors_counter.add(1, {"type": "method_not_found"})
                return JsonRpcResponse(
                    id=request_id,
                    error=JsonRpcError(code=-32601, message=f"Method not found: {validated.method}")
                ).model_dump(exclude_none=True)

            try:
                result = await handler(validated.params, session)

                # Record duration
                duration = time.time() - start_time
                if self.meter:
                    self.request_duration.record(duration, {"method": method})

                if result is None and request_id is None:
                    return None  # Notification

                return JsonRpcResponse(id=request_id, result=result).model_dump(exclude_none=True)

            except ValueError as e:
                self.logger.error("Request error", method=method, error=str(e))
                if self.meter:
                    self.errors_counter.add(1, {"type": "invalid_params"})
                return JsonRpcResponse(
                    id=request_id,
                    error=JsonRpcError(code=-32602, message=str(e))
                ).model_dump(exclude_none=True)

            except Exception as e:
                self.logger.error("Internal error", method=method, error=str(e))
                if self.meter:
                    self.errors_counter.add(1, {"type": "internal"})
                return JsonRpcResponse(
                    id=request_id,
                    error=JsonRpcError(code=-32603, message=f"Internal error: {e}")
                ).model_dump(exclude_none=True)

    def cleanup_session(self, session_id: str):
        """Clean up a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.meter:
                self.active_sessions.add(-1)
            self.logger.info("Session cleaned up", session_id=session_id)


# =============================================================================
# HTTP Transport with Graceful Shutdown
# =============================================================================

class ObservableHTTPTransport:
    """HTTP Transport with full observability"""

    def __init__(self, server: MCPServer, config: Config):
        self.server = server
        self.config = config
        self.app = web.Application()
        self._shutdown_event = asyncio.Event()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_post("/mcp", self._handle_post)
        self.app.router.add_get("/mcp/sse", self._handle_sse)
        self.app.router.add_get("/health", self._handle_health)
        self.app.router.add_get("/ready", self._handle_ready)
        self.app.middlewares.append(self._tracing_middleware)
        self.app.middlewares.append(self._cors_middleware)

    @web.middleware
    async def _tracing_middleware(self, request: web.Request, handler):
        """Extract trace context from incoming requests"""
        if self.server.tracer:
            propagator = TraceContextTextMapPropagator()
            ctx = propagator.extract(carrier=dict(request.headers))
            # Could attach context here for distributed tracing
        return await handler(request)

    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler):
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Session-ID, traceparent, tracestate"
        return response

    async def _get_or_create_session(self, request: web.Request) -> MCPSession:
        session_id = request.headers.get("X-Session-ID")
        if session_id and session_id in self.server.sessions:
            session = self.server.sessions[session_id]
            session.last_activity = time.time()
            return session

        session_id = str(uuid.uuid4())
        session = MCPSession(session_id=session_id)
        self.server.sessions[session_id] = session
        return session

    async def _handle_post(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status=400)

        session = await self._get_or_create_session(request)

        if isinstance(body, list):
            responses = [await self.server.handle_request(req, session) for req in body]
            responses = [r for r in responses if r]
            return web.json_response(responses, headers={"X-Session-ID": session.session_id})

        response = await self.server.handle_request(body, session)
        if response is None:
            return web.Response(status=204, headers={"X-Session-ID": session.session_id})
        return web.json_response(response, headers={"X-Session-ID": session.session_id})

    async def _handle_sse(self, request: web.Request) -> web.StreamResponse:
        session = await self._get_or_create_session(request)
        session.sse_queue = asyncio.Queue()

        self.server.logger.info("SSE connection established", session_id=session.session_id)

        async with sse_response(request) as resp:
            await resp.send(json.dumps({"type": "connected", "sessionId": session.session_id}), event="connection")

            try:
                while not self._shutdown_event.is_set():
                    try:
                        event = await asyncio.wait_for(session.sse_queue.get(), timeout=30.0)
                        await resp.send(json.dumps(event), event="message")
                    except asyncio.TimeoutError:
                        await resp.send("", event="ping")
            except asyncio.CancelledError:
                pass
            finally:
                session.sse_queue = None

        return resp

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({
            "status": "healthy",
            "server": self.config.SERVER_NAME,
            "version": self.config.SERVER_VERSION
        })

    async def _handle_ready(self, request: web.Request) -> web.Response:
        """Kubernetes readiness probe"""
        return web.json_response({"ready": True})

    async def _cleanup_sessions(self):
        """Periodic session cleanup"""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(60)
            now = time.time()
            stale = [sid for sid, s in self.server.sessions.items() if now - s.last_activity > 3600]
            for sid in stale:
                self.server.cleanup_session(sid)

    async def _on_shutdown(self, app):
        """Graceful shutdown handler"""
        self.server.logger.info("Shutting down...")
        self._shutdown_event.set()

        # Close all SSE connections
        for session in self.server.sessions.values():
            if session.sse_queue:
                await session.sse_queue.put({"type": "shutdown"})

    def run(self):
        """Start server with graceful shutdown"""
        self.app.on_shutdown.append(self._on_shutdown)

        # Start session cleanup task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.server.logger.info("Starting MCP server",
                               host=self.config.HOST,
                               port=self.config.PORT,
                               otel_enabled=self.config.OTEL_ENABLED,
                               metrics_port=self.config.METRICS_PORT if self.config.METRICS_ENABLED else None)

        web.run_app(
            self.app,
            host=self.config.HOST,
            port=self.config.PORT,
            print=None,
            handle_signals=True
        )


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server with Observability")
    parser.add_argument("--host", default=None, help="Host (env: MCP_HOST)")
    parser.add_argument("--port", type=int, default=None, help="Port (env: MCP_PORT)")
    parser.add_argument("--otel-exporter", choices=["console", "otlp"], default=None)
    parser.add_argument("--no-otel", action="store_true", help="Disable OpenTelemetry")
    parser.add_argument("--no-metrics", action="store_true", help="Disable metrics")

    args = parser.parse_args()

    config = Config()

    # Override from CLI args
    if args.host:
        config.HOST = args.host
    if args.port:
        config.PORT = args.port
    if args.otel_exporter:
        config.OTEL_EXPORTER = args.otel_exporter
    if args.no_otel:
        config.OTEL_ENABLED = False
    if args.no_metrics:
        config.METRICS_ENABLED = False

    server = MCPServer(config)
    transport = ObservableHTTPTransport(server, config)
    transport.run()


if __name__ == "__main__":
    main()
