
from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.utils import send_json, recv_json

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8888

class QuizServer:
    def __init__(self, host: str, port: int, questions: List[dict]):
        self.host = host
        self.port = port
        self.questions = questions
        self.clients: Dict[int, Dict] = {}
        self.scores: Dict[str, int] = {}
        self.lock = threading.Lock()
        self.current_question: Optional[dict] = None
        self.first_correct_awarded: bool = False
        self.answered_users: set[str] = set()
        self._srv_sock: Optional[socket.socket] = None
        self._running = False
        self._start_event = threading.Event()  # new event for manual start

    def start(self) -> None:
        print(f"Starting QuizServer on {self.host}:{self.port}")
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(32)
        self._srv_sock = srv
        self._running = True

        accept_thread = threading.Thread(target=self._accept_loop, args=(srv,), daemon=True)
        accept_thread.start()

        print("Waiting for players to connect...")
        print("Type 'start' and press Enter to begin the quiz.")

        # Manual start trigger
        while not self._start_event.is_set():
            cmd = input().strip().lower()
            if cmd == "start":
                self._start_event.set()
                print("Starting the quiz!")

        try:
            if not self.questions:
                print("⚠️ No questions loaded. Check your JSON path.")
                return

            for q in self.questions:
                with self.lock:
                    self.current_question = q
                    self.first_correct_awarded = False
                    self.answered_users = set()

                q_msg = {
                    "type": "question",
                    "id": q["id"],
                    "question": q["question"],
                    "choices": q["choices"],
                    "time": q.get("time", 10),
                }
                print(f"Broadcasting question {q['id']}: {q['question']}")
                self.broadcast(q_msg)

                total = int(q.get("time", 10))
                for _ in range(total):
                    time.sleep(1)
                    if not self._running:
                        break

                correct = q.get("answer")
                reveal_msg = {"type": "broadcast", "message": f"Time is up! Correct answer: {correct}"}
                self.broadcast(reveal_msg)
                self._broadcast_scores()

            end_msg = {"type": "end", "msg": "Game over!", "final_scores": self.scores}
            self.broadcast(end_msg)
            print("Game finished, shutting down server loop.")
        except KeyboardInterrupt:
            print("Server interrupted by user; shutting down.")
        finally:
            self._running = False
            if self._srv_sock:
                try:
                    self._srv_sock.close()
                except OSError:
                    pass
            with self.lock:
                for info in list(self.clients.values()):
                    try:
                        info.get("sock").close()
                    except OSError:
                        pass
                self.clients.clear()

    def _accept_loop(self, srv_sock: socket.socket) -> None:
        print("Accept thread started; waiting for connections...")
        while self._running:
            try:
                client_sock, addr = srv_sock.accept()
                print(f"New connection from {addr}")
                th = threading.Thread(target=self._client_thread, args=(client_sock,), daemon=True)
                th.start()
            except OSError:
                break

    def _client_thread(self, sock: socket.socket) -> None:
        fileno = sock.fileno()
        username: Optional[str] = None
        try:
            while True:
                msg = recv_json(sock)
                if msg is None:
                    print(f"Client {fileno} disconnected")
                    break
                mtype = msg.get("type")

                if mtype == "join":
                    candidate = str(msg.get("username", "")).strip()
                    username = candidate if candidate else f"guest-{fileno}"
                    with self.lock:
                        self.clients[fileno] = {"sock": sock, "username": username}
                        if username not in self.scores:
                            self.scores[username] = 0
                    print(f"Registered user '{username}' (fd={fileno})")
                    send_json(sock, {"type": "join_ack", "msg": f"Welcome {username}!"})
                elif mtype == "answer":
                    qid = msg.get("question_id")
                    answer = msg.get("answer")
                    uname = (msg.get("username") or username or "").strip()
                    if not uname:
                        send_json(sock, {"type": "error", "detail": "username not provided"})
                        continue
                    with self.lock:
                        if self.current_question is None or self.current_question.get("id") != qid:
                            send_json(sock, {"type": "feedback", "correct": False, "detail": "question mismatch or late"})
                            continue
                        if uname in self.answered_users:
                            send_json(sock, {"type": "feedback", "correct": False, "detail": "already answered"})
                            continue
                        self.answered_users.add(uname)
                        correct = str(self.current_question.get("answer")).strip()
                        is_correct = str(answer).strip() == correct
                        if (not self.first_correct_awarded) and is_correct:
                            self.scores[uname] = self.scores.get(uname, 0) + 1
                            self.first_correct_awarded = True
                            send_json(sock, {"type": "feedback", "correct": True})
                            self._broadcast_scores()
                        else:
                            send_json(sock, {"type": "feedback", "correct": False})
        finally:
            with self.lock:
                if fileno in self.clients:
                    self.clients.pop(fileno, None)
            try:
                sock.close()
            except OSError:
                pass

    def broadcast(self, msg: dict) -> None:
        to_remove: List[int] = []
        with self.lock:
            items = list(self.clients.items())
        for fileno, info in items:
            sock = info.get("sock")
            ok = send_json(sock, msg)
            if not ok:
                to_remove.append(fileno)
        if to_remove:
            with self.lock:
                for f in to_remove:
                    info = self.clients.pop(f, None)
                    if info:
                        try:
                            info.get("sock").close()
                        except OSError:
                            pass

    def _broadcast_scores(self) -> None:
        msg = {"type": "score", "scores": self.scores}
        self.broadcast(msg)

def load_questions(path: Path) -> List[dict]:
    if not path.exists():
        print(f"Questions file not found: {path}")
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def parse_args():
    p = argparse.ArgumentParser(description="TCP quiz server")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--questions", default=str(ROOT / "questions" / "sample_questions.json"))
    return p.parse_args()

def main():
    args = parse_args()
    questions = load_questions(Path(args.questions))
    server = QuizServer(args.host, args.port, questions)
    server.start()

if __name__ == "__main__":
    main()
