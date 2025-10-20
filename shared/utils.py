
"""shared.utils
Utility helpers for sending and receiving newline-delimited JSON (LD-JSON)
over a blocking TCP socket.
"""
from __future__ import annotations

import json
import socket
from typing import Any, Optional

def send_json(sock: socket.socket, obj: Any) -> bool:
    try:
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n"
        sock.sendall(raw)
        return True
    except (BrokenPipeError, ConnectionResetError, OSError):
        return False

def recv_json(sock: socket.socket) -> Optional[object]:
    buffer = bytearray()
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                return None
            buffer.extend(chunk)
            if b"\n" in chunk:
                break
        line, _, _ = bytes(buffer).partition(b"\n")
        try:
            return json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            return None
    except (ConnectionResetError, OSError):
        return None
