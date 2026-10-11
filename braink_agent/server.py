"""Loopback control runtime. Public routes disclose static contracts only."""
from __future__ import annotations
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit
from .manager import Manager, ROOT
from .adapters import Dispatch

CATALOGUE = {
    "name": "BRAINK_AGENT", "version": "0.1.0", "mode": "PUBLIC_CONTRACT_VIEW",
    "services": [
        {"name": "BRAINK", "purpose": "Identity, purpose, continuation and service coordination"},
        {"name": "IL-LLM", "purpose": "Native durable memory; no model inference binding implied"},
        {"name": "KEX / VFS", "purpose": "Content-addressed artifacts, bindings and receipt readback"},
        {"name": "ToT", "purpose": "Native control evaluation; authentication is enforced separately"},
        {"name": "Native teams", "purpose": "Bounded workers with leases and independent-process observation"},
        {"name": "Keddeh MCP", "purpose": "Existing owner-authenticated cloud service integration"}],
    "boundaries": ["Live service state requires owner access", "No qualified model binding configured",
                   "Actor execution, durable readback and independent assessment remain distinct"],
}

def operations(manager: Manager, name: str, args: dict, service=None) -> dict:
    if not isinstance(args, dict):
        raise ValueError("OBJECT_REQUIRED")
    if name.startswith("cloud_"):
        if service is None:
            raise ValueError("EXISTING_NATIVE_CREDENTIAL_BINDING_REQUIRED")
        if name == "cloud_registry" and not args:
            return service.registry()
        if name == "cloud_dispatch" and set(args) == {"request"}:
            return manager.dispatch(service, Dispatch(**args["request"]))
        if name == "cloud_reconcile" and set(args) == {"command_id"}:
            return manager.reconcile(service, args["command_id"])
        if name == "cloud_connection_readback" and set(args) == {"request_id"}:
            return service.connection_readback(args["request_id"])
        if name == "cloud_connect" and set(args) == {"request_id", "purpose"}:
            # This native operation is read-only with a durable request identity.
            result = service.connect(args["request_id"], args["purpose"])
            observed = service.connection_readback(args["request_id"])
            return {"actor": result, "readback": observed, "assessmentReceipt": None}
        raise ValueError("UNADMITTED_CLOUD_OPERATION")
    routes = {
        "birth": (manager.birth, {"key", "purpose"}),
        "enqueue": (manager.enqueue, {"team_id", "role", "key", "text"}),
        "run": (manager.run, {"team_id", "role"}),
        "verify": (manager.verify, {"team_id", "job_id"}),
        "remember": (manager.remember, {"key", "value"}),
        "recall": (manager.recall, {"key"}),
        "admit_sector": (manager.admit_sector, {"record"}),
        "undertake": (manager.undertake, {"key", "purpose", "circuit", "shell"}),
    }
    if name not in routes:
        raise ValueError("UNADMITTED_OPERATION")
    fn, fields = routes[name]
    if set(args) != fields:
        raise ValueError("EXACT_ARGUMENTS_REQUIRED")
    return fn(**args)

class Handler(BaseHTTPRequestHandler):
    server_version = "BRAINK_AGENT"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *args):
        pass  # Never log authorization, paths containing identifiers, or payloads.

    def valid_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def owner(self):
        token = self.server.owner_token
        expected_origin = "http://" + self.headers.get("Host", "")
        return bool(token and self.headers.get("Origin", expected_origin) == expected_origin and
            hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token))

    def send(self, status, body, media="application/json"):
        data = json.dumps(body, allow_nan=False).encode() if media == "application/json" else body
        self.send_response(status)
        self.send_header("Content-Type", media + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.valid_host():
            return self.send(421, {"error": "HOST_REJECTED"})
        path = urlsplit(self.path).path
        if path == "/api/public":
            return self.send(200, CATALOGUE)
        if path == "/health":
            return self.send(200, {"service": "BRAINK_AGENT", "status": "SERVING", "cloud": "NOT_PROBED"})
        if path == "/api/owner":
            if not self.owner():
                return self.send(401, {"error": "OWNER_AUTHENTICATION_REQUIRED"})
            return self.send(200, self.server.manager.overview())
        assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                  "/style.css": ("style.css", "text/css")}
        if path in assets:
            filename, media = assets[path]
            return self.send(200, (ROOT / "web" / filename).read_bytes(), media)
        self.send(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        if not self.valid_host():
            return self.send(421, {"error": "HOST_REJECTED"})
        if not self.owner():
            self.close_connection = True
            return self.send(401, {"error": "OWNER_AUTHENTICATION_REQUIRED"})
        if self.path != "/api/owner/operate":
            return self.send(404, {"error": "NOT_FOUND"})
        try:
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Type") != "application/json":
                raise ValueError("JSON_CONTENT_REQUIRED")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 100000:
                raise ValueError("REQUEST_BOUND")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict) or set(body) != {"operation", "arguments"}:
                raise ValueError("EXACT_ENVELOPE_REQUIRED")
            result = operations(self.server.manager, body["operation"], body["arguments"], self.server.service)
            self.send(200, result)
        except (ValueError, KeyError, TypeError):
            self.send(400, {"error": "INVALID_OR_CONFLICTING_REQUEST"})
        except Exception:
            self.send(409, {"error": "OPERATION_INCOMPLETE_RECONCILE_STATE"})

def make_server(root: Path, port: int, owner_token: str | None = None, service=None):
    if owner_token is not None and (len(owner_token) < 24 or any(c.isspace() for c in owner_token)):
        raise ValueError("EXISTING_STRONG_OWNER_CREDENTIAL_REQUIRED")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.manager, server.owner_token = Manager(root), owner_token
    server.service = service
    return server
