#!/usr/bin/env python3
"""
archon_acp_plugin.py

A minimal Zed ACP plugin written in Python that forwards a subset of
RPC calls to the Archon MCP server.

The plugin expects the Zed environment variable `ZED_ACP_SOCKET` to be
set to the Unix socket path that Zed uses for ACP communication.
It also reads `MCP_URL` from the environment, defaulting to
`http://localhost:8051`.

Supported RPC methods:
  - archon.getProjects
  - archon.createTask
  - archon.searchKnowledge

Responses are returned using the standard ACP JSON-RPC format.
"""

import json
import os
import sys
import socket
import threading
from urllib.parse import urljoin
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    print("The 'requests' library is required to run this plugin.", file=sys.stderr)
    sys.exit(1)


class ACPConnection:
    """Handles the low‑level socket communication with Zed."""
    def __init__(self, socket_path: str):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.sock.connect(socket_path)
        except Exception as e:
            print(f"Could not connect to Zed ACP socket {socket_path}: {e}", file=sys.stderr)
            sys.exit(1)
        self.lock = threading.Lock()

    def send(self, payload: Dict[str, Any]) -> None:
        """Send a JSON message to Zed."""
        data = json.dumps(payload).encode("utf-8") + b"\n"
        with self.lock:
            self.sock.sendall(data)

    def recv(self) -> Optional[Dict[str, Any]]:
        """Receive a single JSON message from Zed."""
        buffer = b""
        while True:
            chunk = self.sock.recv(4096)
            if not chunk:
                return None  # socket closed
            buffer += chunk
            if b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    return json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    # malformed line – ignore and continue
                    continue


class ArchonClient:
    """Simple HTTP client to talk to the Archon MCP server."""
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/") + "/"

    def get_projects(self) -> Any:
        resp = requests.get(urljoin(self.base, "api/projects"))
        resp.raise_for_status()
        return resp.json()

    def create_task(self, project_id: str, title: str, assignee: str) -> Any:
        payload = {
            "project_id": project_id,
            "title": title,
            "assignee": assignee,
        }
        resp = requests.post(urljoin(self.base, "api/projects/{}/tasks".format(project_id)),
                             json=payload)
        resp.raise_for_status()
        return resp.json()

    def search_knowledge(self, query: str) -> Any:
        payload = {"query": query}
        resp = requests.post(urljoin(self.base, "api/knowledge/search"),
                             json=payload)
        resp.raise_for_status()
        return resp.json()


def main():
    socket_path = os.getenv("ZED_ACP_SOCKET")
    if not socket_path:
        print("ZED_ACP_SOCKET environment variable not set.", file=sys.stderr)
        sys.exit(1)

    mcp_url = os.getenv("MCP_URL", "http://localhost:8051")
    archon = ArchonClient(mcp_url)
    acp = ACPConnection(socket_path)

    print("Archon ACP plugin started.", file=sys.stderr)

    while True:
        request = acp.recv()
        if request is None:
            break  # socket closed

        # Validate basic JSON-RPC fields
        method = request.get("method")
        params = request.get("params", {})
        req_id = request.get("id", 0)

        if not method:
            acp.send({"id": req_id, "error": {"code": -32600, "message": "Invalid Request"}})
            continue

        try:
            if method == "archon.getProjects":
                result = archon.get_projects()
                acp.send({"id": req_id, "result": result})
            elif method == "archon.createTask":
                # Expecting params: {project_id, title, assignee}
                project_id = params["project_id"]
                title = params["title"]
                assignee = params["assignee"]
                result = archon.create_task(project_id, title, assignee)
                acp.send({"id": req_id, "result": result})
            elif method == "archon.searchKnowledge":
                query = params["query"]
                result = archon.search_knowledge(query)
                acp.send({"id": req_id, "result": result})
            else:
                acp.send({"id": req_id,
                          "error": {"code": -32601, "message": f"Method {method} not found"}})
        except Exception as exc:
            acp.send({"id": req_id,
                      "error": {"code": -32000, "message": str(exc)}})

    print("Archon ACP plugin exiting.", file=sys.stderr)


if __name__ == "__main__":
    main()
