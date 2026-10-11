import argparse
import json
import os
from pathlib import Path
from .manager import Manager
from .server import make_server, operations
from .adapters import KeddehService, MCPTransport

def main():
    parser = argparse.ArgumentParser(description="BRAINK_AGENT native services manager")
    parser.add_argument("--state", type=Path, default=Path.home() / ".local/state/braink-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8787)
    sub.add_parser("status")
    operate = sub.add_parser("operate", help="Read an exact operation/arguments JSON object from stdin")
    args = parser.parse_args()
    cloud_file = os.environ.get("BRAINK_NATIVE_TOKEN_FILE")
    service = KeddehService(MCPTransport(Path(cloud_file).read_text().strip())) if cloud_file else None
    if args.command == "serve":
        token_file = os.environ.get("BRAINK_OWNER_TOKEN_FILE")
        token = Path(token_file).read_text().strip() if token_file else None
        server = make_server(args.state, args.port, token, service)
        print(f"BRAINK_AGENT http://127.0.0.1:{server.server_port} owner={'enabled' if token else 'disabled'}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    else:
        manager = Manager(args.state)
        if args.command == "status":
            result = manager.overview()
        else:
            import sys
            raw = sys.stdin.buffer.read(100001)
            if len(raw) > 100000:
                raise ValueError("INPUT_BOUND")
            payload = json.loads(raw)
            result = operations(manager, payload["operation"], payload["arguments"], service)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
