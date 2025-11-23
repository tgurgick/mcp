# MCP Troubleshooting Guide

This guide helps you diagnose and fix common MCP implementation issues.

## Quick Diagnostics

Run the diagnostic suite to identify issues:

```bash
# Full diagnostic
python mcp_diagnostics.py --server http://localhost:8000

# Verbose output
python mcp_diagnostics.py --server http://localhost:8000 -v

# Specific categories
python mcp_diagnostics.py --server http://localhost:8000 --tests transport,protocol

# Test stdio transport
python mcp_diagnostics.py --stdio --command "python mcp_stdio_server.py"
```

---

## Issue Categories

### 1. Transport Layer Issues

#### Server Not Reachable

**Symptoms:**
- `Connection refused`
- `Cannot connect to host`
- Timeout on all requests

**Diagnostic Test:** `Server Reachable`

**Checklist:**
```bash
# Check if server is running
ps aux | grep mcp_server

# Check if port is in use
lsof -i :8000
netstat -tlnp | grep 8000

# Test basic connectivity
curl http://localhost:8000/health
```

**Common Fixes:**
| Problem | Solution |
|---------|----------|
| Server not started | `python mcp_server.py --port 8000` |
| Wrong port | Check `--port` argument or `MCP_PORT` env var |
| Firewall blocking | `sudo ufw allow 8000/tcp` |
| Binding to wrong interface | Use `--host 0.0.0.0` for all interfaces |

---

#### Health Endpoint Not Responding

**Symptoms:**
- 404 on `/health`
- No JSON response

**Diagnostic Test:** `Health Endpoint`

**Check:**
```bash
curl -v http://localhost:8000/health
```

**Fixes:**
- Ensure you're running the correct server version
- Check server logs for startup errors
- Verify routes are registered

---

#### SSE Endpoint Issues

**Symptoms:**
- Cannot establish SSE connection
- No notifications received
- Wrong Content-Type

**Diagnostic Test:** `SSE Endpoint`

**Check:**
```bash
# Check SSE endpoint
curl -N http://localhost:8000/mcp/sse

# Should see:
# Content-Type: text/event-stream
# data: {"type":"connected"...}
```

**Common Issues:**
| Issue | Cause | Fix |
|-------|-------|-----|
| 404 on /mcp/sse | Route not registered | Check server routes |
| Wrong Content-Type | Missing SSE middleware | Use `aiohttp-sse` |
| Connection closes | No keepalive | Implement ping events |
| CORS error | Missing headers | Add CORS middleware |

---

### 2. Protocol Layer Issues

#### Invalid JSON-RPC Response

**Symptoms:**
- Missing `jsonrpc` field
- Missing `id` field
- No `result` or `error`

**Diagnostic Test:** `JSON-RPC Format`

**Expected Response Format:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { ... }
}
```

**Or for errors:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid request"
  }
}
```

**Check:**
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}' | jq
```

---

#### Error Codes Reference

| Code | Name | Meaning |
|------|------|---------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Not a valid JSON-RPC request |
| -32601 | Method not found | Method doesn't exist |
| -32602 | Invalid params | Wrong parameters |
| -32603 | Internal error | Server error |

---

### 3. Initialization Issues

#### Initialize Handshake Fails

**Symptoms:**
- Error on `initialize` method
- Missing capabilities in response
- Protocol version mismatch

**Diagnostic Test:** `Initialize Handshake`

**Correct Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "clientInfo": {
      "name": "my-client",
      "version": "1.0.0"
    }
  }
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true }
    },
    "serverInfo": {
      "name": "mcp-server",
      "version": "1.0.0"
    }
  }
}
```

**Common Issues:**
| Issue | Cause | Fix |
|-------|-------|-----|
| Missing protocolVersion | Server bug | Check _handle_initialize |
| Wrong version | Version mismatch | Use `2024-11-05` |
| Missing capabilities | Incomplete response | Return all capability objects |

---

#### Session Not Persisting

**Symptoms:**
- New session ID each request
- State not maintained
- Subscriptions lost

**Diagnostic Test:** `Session Persistence`

**Check:**
```bash
# First request - note X-Session-ID
curl -v -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{...}}'

# Second request - use same session
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: <session-id-from-above>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"ping","params":{}}'
```

**Fixes:**
- Ensure server stores sessions in a dict
- Check session lookup logic
- Verify header name is exactly `X-Session-ID`

---

### 4. Tools Issues

#### Tool Not Found

**Symptoms:**
- Error `-32602` on `tools/call`
- Tool not in `tools/list`

**Diagnostic Test:** `List Tools`, `Call Tool`

**Debug Steps:**
```bash
# List all tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq '.result.tools[].name'

# Call specific tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_current_time","arguments":{}}}' | jq
```

**Common Issues:**
| Issue | Cause | Fix |
|-------|-------|-----|
| Tool not listed | Not registered | Add to `_tools` dict |
| Wrong name | Typo | Check exact name |
| Missing handler | No execution code | Add to `_execute_tool` |

---

#### Tool Execution Error

**Symptoms:**
- `isError: true` in response
- Exception during execution

**Check server logs:**
```bash
# Run server with debug logging
LOG_LEVEL=DEBUG python mcp_server.py
```

**Common Issues:**
| Issue | Cause | Fix |
|-------|-------|-----|
| Missing argument | Required param not provided | Check inputSchema |
| Type error | Wrong argument type | Validate/convert types |
| Internal error | Bug in tool code | Check tool implementation |

---

### 5. Resource Issues

#### Resource Not Found

**Symptoms:**
- Error on `resources/read`
- Resource not in list

**Diagnostic Test:** `List Resources`, `Read Resource`

**Debug:**
```bash
# List resources
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"resources/list","params":{}}' | jq '.result.resources[].uri'

# Read specific resource
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"resources/read","params":{"uri":"server://status"}}' | jq
```

---

#### Subscription Not Working

**Symptoms:**
- No notifications on resource change
- `resources/subscribe` succeeds but nothing happens

**Check:**
1. Is SSE connection established?
2. Is resource URI in subscribed set?
3. Is notification being sent to queue?

**Debug with logging:**
```python
# In _notify_resource_changed:
logger.info(f"Notifying {len(subscribers)} subscribers about {uri}")
```

---

### 6. SSE/Notification Issues

#### No Notifications Received

**Symptoms:**
- SSE connects but no events
- Progress updates not shown

**Diagnostic Test:** `SSE Connection`, `Progress Notifications`

**Debug Checklist:**
- [ ] SSE connection established (check for `connection` event)
- [ ] Session has `sse_queue` assigned
- [ ] Notifications are put in queue
- [ ] Events are formatted correctly

**Test manually:**
```bash
# Terminal 1: Start SSE listener
curl -N http://localhost:8000/mcp/sse

# Terminal 2: Trigger action that should notify
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"long_running_task","arguments":{"steps":3}}}'
```

---

### 7. Client Issues

#### Connection Timeout

**Symptoms:**
- Client hangs on connect
- Timeout errors

**Fixes:**
```python
# Increase timeout
client = MCPClient(server_url, timeout=30)

# Check network
ping localhost
curl http://localhost:8000/health
```

---

#### Session Lost After Reconnect

**Symptoms:**
- State lost after network hiccup
- Need to re-initialize

**Solution:**
```python
# Store session ID and reuse
async def reconnect():
    client = MCPClient(server_url)
    client.session_id = saved_session_id  # Restore session
    await client.ping()  # Verify connection
```

---

## Diagnostic Output Reference

### Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| `transport` | Server Reachable, Health, MCP Endpoint, SSE | Network connectivity |
| `protocol` | JSON-RPC Format, Error Handling, Parse Error | Protocol compliance |
| `initialization` | Initialize, Session Persistence | Handshake flow |
| `tools` | List, Call, Validation | Tool functionality |
| `resources` | List, Read | Resource access |
| `prompts` | List | Prompt availability |
| `sse` | Connection, Progress | Notifications |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Some tests failed |
| 2 | Critical failure (couldn't connect) |

---

## Quick Reference: Common Fixes

### Server Won't Start

```bash
# Check port in use
lsof -i :8000

# Kill existing process
kill $(lsof -t -i:8000)

# Check dependencies
pip install -r requirements.txt

# Run with verbose logging
python mcp_server.py 2>&1 | tee server.log
```

### Client Can't Connect

```bash
# Test connectivity
curl http://localhost:8000/health

# Check firewall
sudo ufw status

# Try different host
python mcp_client.py --server http://127.0.0.1:8000
```

### No Response from Server

```bash
# Check server logs
tail -f server.log

# Test with simple request
echo '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}' | \
  curl -X POST http://localhost:8000/mcp \
    -H "Content-Type: application/json" \
    -d @-
```

### SSE Not Working

```bash
# Test SSE directly
curl -N -H "Accept: text/event-stream" http://localhost:8000/mcp/sse

# Check CORS if from browser
curl -H "Origin: http://localhost:3000" http://localhost:8000/mcp/sse
```

---

## Getting Help

1. Run full diagnostics: `python mcp_diagnostics.py -v`
2. Check server logs with `LOG_LEVEL=DEBUG`
3. Review this troubleshooting guide
4. Check the MCP specification at https://spec.modelcontextprotocol.io/
