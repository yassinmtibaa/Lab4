"""Small helpers for newline-delimited JSON over sockets.

Functions:
- send_json(sock, obj): send a JSON object followed by newline
- recv_json(sock): recv until newline and parse JSON
"""
import json


def send_json(sock, obj):
    data = json.dumps(obj, separators=(",", ":")) + "\n"
    sock.sendall(data.encode("utf-8"))


def recv_json(sock):
    buf = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            # connection closed
            return None
        buf.extend(chunk)
        if b"\n" in chunk:
            break
    line, _, rest = bytes(buf).partition(b"\n")
    # Note: any extra bytes after newline will be discarded in this simple helper
    try:
        return json.loads(line.decode("utf-8"))
    except Exception:
        return None
