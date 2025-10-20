"""Automated test client for the TCP quiz server.

Usage: run this while the server is running. It will connect, join as
"tester", wait for a question message, answer with the first choice, and
print server responses.
"""
import socket
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.utils import send_json, recv_json


def main():
    host = "127.0.0.1"
    port = 8888
    print(f"Connecting to {host}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    send_json(sock, {"type": "join", "username": "tester"})

    start = time.time()
    while True:
        msg = recv_json(sock)
        if msg is None:
            print("Connection closed")
            break
        print("RECV:", msg)
        if msg.get("type") == "question":
            qid = msg.get("id")
            choices = msg.get("choices") or []
            answer = choices[0] if choices else ""
            print(f"Answering question {qid} with '{answer}'")
            send_json(sock, {"type": "answer", "username": "tester", "question_id": qid, "answer": answer})
        if msg.get("type") == "end":
            break
        if time.time() - start > 30:
            print("Timeout waiting for messages")
            break


if __name__ == "__main__":
    main()
