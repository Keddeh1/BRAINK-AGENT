"""Typed, bounded adapters to the existing owner-protected Keddeh MCP service.

Transport credentials are supplied by an existing authenticated binding. They are
never minted, written to state, or returned to the control interface.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Any, Protocol
import urllib.request
import urllib.error
import uuid

ENDPOINT = "https://keddeh-systems-runtime.aboudy65097.chatgpt.site/mcp"
MAX_RESPONSE = 2 * 1024 * 1024
READ_TOOLS = frozenset({"agent_registry", "development_status", "command_status",
    "outbound_connection_catalogue", "outbound_connection_status", "vfs_list",
    "vfs_read", "vfs_commit_status", "read_resolve_receipt"})
WRITE_TOOLS = frozenset({"agent_dispatch", "vfs_put", "outbound_connection_request"})

class ToolTransport(Protocol):
    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...

class BoundaryError(RuntimeError):
    """A transport outcome is not proof that a remote mutation did not occur."""

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise BoundaryError("REDIRECT_REJECTED")

class MCPTransport:
    def __init__(self, token: str, endpoint: str = ENDPOINT):
        if endpoint != ENDPOINT:
            raise ValueError("UNADMITTED_SERVICE_ENDPOINT")
        if not token or len(token) > 16384 or any(c.isspace() for c in token):
            raise ValueError("EXISTING_OWNER_CREDENTIAL_REQUIRED")
        self.endpoint, self._token, self._session = endpoint, token, None
        self._opener = urllib.request.build_opener(NoRedirect())
        self._initialized = False

    def _rpc(self, method: str, params: dict, notification: bool = False) -> dict:
        rid = str(uuid.uuid4())
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            payload["id"] = rid
        data = json.dumps(payload).encode()
        if len(data) > 140000:
            raise ValueError("REQUEST_BYTE_BOUND")
        headers = {"Authorization": "Bearer " + self._token,
                   "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": "2025-03-26"}
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        request = urllib.request.Request(self.endpoint, data=data, headers=headers)
        try:
            with self._opener.open(request, timeout=15) as response:
                raw = response.read(MAX_RESPONSE + 1)
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    if len(session) > 256 or any(c.isspace() for c in session):
                        raise BoundaryError("INVALID_SESSION")
                    self._session = session
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as error:
            raise BoundaryError("AUTHENTICATION_ACTION_REQUIRED" if error.code == 401 else
                                "ACCESS_DENIED" if error.code == 403 else "BACKEND_HTTP_FAILURE") from None
        except (OSError, TimeoutError):
            raise BoundaryError("UNCERTAIN_TRANSPORT_RECONCILE_BEFORE_REPLAY") from None
        if len(raw) > MAX_RESPONSE:
            raise BoundaryError("RESPONSE_BYTE_BOUND")
        if notification and not raw:
            return {}
        try:
            if "text/event-stream" in content_type:
                messages = []
                for event in raw.decode().replace("\r\n", "\n").split("\n\n"):
                    body = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
                    if body:
                        messages.append(json.loads(body))
                result = next(m for m in messages if m.get("id") == rid)
            else:
                result = json.loads(raw)
            if result.get("id") != rid or "error" in result:
                raise BoundaryError("RPC_REJECTED")
            return result["result"]
        except (ValueError, KeyError, StopIteration, TypeError):
            raise BoundaryError("PROTOCOL_FAILURE") from None

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in READ_TOOLS | WRITE_TOOLS:
            raise ValueError("UNADMITTED_TOOL")
        if not self._initialized:
            self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                "clientInfo": {"name": "BRAINK_AGENT", "version": "0.1.0"}})
            self._rpc("notifications/initialized", {}, notification=True)
            self._initialized = True
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise BoundaryError("NATIVE_TOOL_REJECTED")
        if isinstance(result.get("structuredContent"), dict):
            return result["structuredContent"]
        try:
            value = json.loads(next(c["text"] for c in result["content"] if c.get("type") == "text"))
        except (KeyError, ValueError, StopIteration, TypeError):
            raise BoundaryError("TOOL_RESULT_NOT_JSON") from None
        if value is None and name in {"command_status", "vfs_commit_status", "outbound_connection_status"}:
            return {"state": "NOT_FOUND", "record": None}
        if not isinstance(value, dict):
            raise BoundaryError("TOOL_RESULT_NOT_OBJECT")
        return value

@dataclass(frozen=True)
class Dispatch:
    command_id: str
    capability_id: str
    namespace_id: str
    expected_version: int
    input: dict[str, Any]
    rationale: dict[str, Any]

class KeddehService:
    def __init__(self, transport: ToolTransport):
        self.transport = transport

    def registry(self) -> dict:
        return self.transport.call("agent_registry", {})

    def readback(self, command_id: str) -> dict:
        return self.transport.call("command_status", {"commandId": command_id})

    def dispatch(self, request: Dispatch) -> dict:
        if type(request.expected_version) is not int or request.expected_version < 0:
            raise ValueError("EXPECTED_VERSION_REQUIRED")
        required = {"objective", "reason", "evidence", "expectedEffect", "rollback", "impact"}
        if not required <= request.rationale.keys():
            raise ValueError("RATIONALE_REQUIRED")
        return self.transport.call("agent_dispatch", {"commandId": request.command_id,
            "capabilityId": request.capability_id, "namespaceId": request.namespace_id,
            "expectedVersion": request.expected_version, "input": request.input, "rationale": request.rationale})

    def connect(self, request_id: str, purpose: str) -> dict:
        return self.transport.call("outbound_connection_request", {"requestId": request_id,
            "serviceId": "service://keddeh/native-mcp", "purpose": purpose, "operation": "development_status"})

    def connection_readback(self, request_id: str) -> dict:
        return self.transport.call("outbound_connection_status", {"requestId": request_id})

    def vfs_put(self, request_id: str, name: str, content: str) -> dict:
        if len(content.encode()) > 100000:
            raise ValueError("VFS_BYTE_BOUND")
        return self.transport.call("vfs_put", {"requestId": request_id, "name": name, "content": content})

    def vfs_read(self, object_id: str) -> dict:
        return self.transport.call("vfs_read", {"id": object_id})
