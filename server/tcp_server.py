"""Minimal threaded TCP server for broadcasting quiz questions.

Protocol (newline-delimited JSON):
- Server -> clients: {"type":"question","id":int,"question":str,"choices":[...],"time":int}
- Client -> server: {"type":"answer","client_id":str,"question_id":int,"choice":int}
"""
import socket
import threading
import json
import time
from pathlib import Path

from shared.utils import send_json, recv_json


HOST = "0.0.0.0"
PORT = 5001


class ClientHandler(threading.Thread):
    def __init__(self, sock, addr, server):
        super().__init__(daemon=True)
        self.sock = sock
        self.addr = addr
        self.server = server
        self.id = f"{addr[0]}:{addr[1]}"

    def run(self):
        print(f"Client connected: {self.id}")
        try:
            while True:
                msg = recv_json(self.sock)
                if msg is None:
                    break
                if msg.get("type") == "answer":
                    print("Received answer:", msg)
                    # Simple scoring: echo back acknowledgement
                    send_json(self.sock, {"type": "ack", "question_id": msg.get("question_id")})
        finally:
            print(f"Client disconnected: {self.id}")
            self.server.remove_client(self.sock)
            self.sock.close()


class QuizServer:
    def __init__(self, host=HOST, port=PORT, questions_file="questions/sample_questions.json"):
        self.host = host
        self.port = port
        self.questions = self.load_questions(questions_file)
        self.clients = []
        self.lock = threading.Lock()

    def load_questions(self, path):
        p = Path(path)
        if not p.exists():
            return []
        with p.open() as f:
            return json.load(f)

    def start(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen()
        print(f"Quiz server listening on {self.host}:{self.port}")

        threading.Thread(target=self._accept_loop, args=(srv,), daemon=True).start()

        # Simple loop to broadcast questions every 10 seconds
        try:
            for q in self.questions:
                print("Broadcasting question:", q.get("id"))
                self.broadcast({"type": "question", **q})
                # wait time specified in question or default 10s
                time.sleep(q.get("time", 10))
            print("All questions broadcasted. Server will keep running for clients to finish.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down server")

    def _accept_loop(self, srv):
        while True:
            sock, addr = srv.accept()
            with self.lock:
                self.clients.append(sock)
            handler = ClientHandler(sock, addr, self)
            handler.start()

    def broadcast(self, msg):
        with self.lock:
            for c in list(self.clients):
                try:
                    send_json(c, msg)
                except Exception:
                    print("Removing client due to send error")
                    self.remove_client(c)

    def remove_client(self, sock):
        with self.lock:
            if sock in self.clients:
                self.clients.remove(sock)


if __name__ == "__main__":
    server = QuizServer()
    server.start()
