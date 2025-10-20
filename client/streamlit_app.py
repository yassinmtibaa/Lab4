## `client/streamlit_app.py`

"""Streamlit client for the TCP quiz game.

Run with the project's virtualenv active:

    streamlit run client/streamlit_app.py

This app connects to the TCP server, displays questions, accepts answers,
and shows a live leaderboard. Network I/O occurs on a background thread to
avoid blocking Streamlit's main thread.
"""
from __future__ import annotations

from pathlib import Path
import sys
from queue import Queue, Empty
import socket
import threading
import time
from typing import Optional


import streamlit as st

# Optional auto-refresh: `pip install streamlit-autorefresh`
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
except Exception:  # pragma: no cover
    st_autorefresh = None

# Ensure project root importable when running from client/ dir
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.utils import send_json, recv_json

st.set_page_config(page_title="TCP Quiz Player", layout="wide")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8888

# Thread-safe queue where background listener will put incoming server messages.

def ensure_session_state() -> None:
    if "sock" not in st.session_state:
        st.session_state.sock: Optional[socket.socket] = None
    if "listener_stop" not in st.session_state:
        st.session_state.listener_stop = threading.Event()
    if "listener_thread" not in st.session_state:
        st.session_state.listener_thread: Optional[threading.Thread] = None
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "leaderboard" not in st.session_state:
        st.session_state.leaderboard = {}
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "message_queue" not in st.session_state:
        from queue import Queue
        st.session_state.message_queue = Queue()


def connect(host: str, port: int, username: str) -> None:
    # Clean any previous connection
    disconnect()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    sock.connect((host, port))
    sock.settimeout(None)

    st.session_state.sock = sock
    st.session_state.username = username.strip() or "guest"

    # send join
    send_json(sock, {"type": "join", "username": st.session_state.username})

    # start background listener
    st.session_state.listener_stop.clear()
    th = threading.Thread(
    target=listener_thread,
    args=(sock, st.session_state.listener_stop, st.session_state.message_queue),  # 👈 pass the queue
    daemon=True)
    st.session_state.listener_thread = th
    th.start()


def disconnect() -> None:
    # signal stop
    stop_event = st.session_state.get("listener_stop")
    if stop_event:
        stop_event.set()

    # close socket
    sock = st.session_state.get("sock")
    if sock:
        try:
            sock.close()
        except OSError:
            pass
    st.session_state.sock = None
    st.session_state.current_question = None

def listener_thread(sock: socket.socket, stop_event: threading.Event, queue_obj) -> None:
    """Background thread that receives raw server messages and pushes them into the provided queue."""
    print("Listener thread started.")
    while not stop_event.is_set():
        try:
            msg = recv_json(sock)
        except Exception as e:
            print("Listener error:", e)
            break

        if msg is None:
            print("Listener detected server closed.")
            queue_obj.put({"type": "_internal_disconnected", "detail": "server closed"})
            break

        print("Pushing to queue:", msg)
        queue_obj.put(msg)
    print("Listener thread exiting.")


    """Background thread that receives raw server messages and pushes them into MESSAGE_QUEUE."""
    print("Listener thread started.")
    while not stop_event.is_set():
        try:
            msg = recv_json(sock)
        except Exception as e:
            print("Listener error:", e)
            break

        if msg is None:
            print("Listener detected server closed.")
            st.session_state.message_queue.put({"type": "_internal_disconnected", "detail": "server closed"})
            break

        print("Pushing to queue:", msg)
        st.session_state.message_queue.put(msg)
    print("Listener thread exiting.")


def process_incoming_messages():
    """Drain MESSAGE_QUEUE and update st.session_state."""
    needs_rerun = False
    st.write("DEBUG:", st.session_state.get("current_question"))
    while True:
        try:
            msg = st.session_state.message_queue.get_nowait()
        except Empty:
            break

        mtype = msg.get("type")
        if mtype == "question":
            q = msg.copy()
            q["_deadline_ts"] = time.time() + int(q.get("time", 10))
            st.session_state.current_question = q
            st.session_state.messages.append(f"New question: {q.get('question')}")
            needs_rerun = True
        elif mtype == "join_ack":
            st.session_state.messages.append(msg.get("msg"))
        elif mtype == "score":
            st.session_state.leaderboard = msg.get("scores", {})
        elif mtype == "broadcast":
            st.session_state.messages.append(msg.get("message"))
        elif mtype == "feedback":
            st.session_state.messages.append(f"Feedback: correct={msg.get('correct')}")
        elif mtype == "end":
            st.session_state.current_question = None
            st.session_state.messages.append(msg.get("msg"))
            needs_rerun = True
        elif mtype == "_internal_disconnected":
            st.session_state.messages.append("Disconnected from server")
            st.session_state.sock = None

    if needs_rerun:
        st.experimental_rerun()


def send_answer(question_id: int, answer: str) -> None:
    sock = st.session_state.get("sock")
    if not sock:
        st.session_state.messages.append("Not connected")
        return
    payload = {
        "type": "answer",
        "username": st.session_state.username,
        "question_id": question_id,
        "answer": answer,
    }
    send_json(sock, payload)


def render_leaderboard() -> None:
    scores = st.session_state.get("leaderboard") or {}
    if not scores:
        st.write("No scores yet")
        return
    rows = sorted(scores.items(), key=lambda kv: -kv[1])
    for name, pts in rows:
        st.write(f"**{name}** — {pts} pts")
def main():
    ensure_session_state()

    # Auto-refresh the UI every second
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=1000, key="refresh")
    except Exception:
        st.write("ℹ️ Tip: install streamlit-autorefresh for live updates.")
        st.write("   pip install streamlit-autorefresh")

    # --- process any pending messages ---
    process_incoming_messages()

    # --- Debug info ---
    st.write("DEBUG current_question:", st.session_state.get("current_question"))
    st.write("DEBUG queue size:", st.session_state.message_queue.qsize())

    st.title("TCP Quiz — Player")

    with st.sidebar:
        host = st.text_input("Server host", value=DEFAULT_HOST)
        port = st.number_input("Server port", value=DEFAULT_PORT, step=1)
        username = st.text_input("Username", value=st.session_state.get("username", ""))

        if st.session_state.get("sock") is None:
            if st.button("Connect"):
                try:
                    connect(host, int(port), username)
                except Exception as e:
                    st.error(f"Failed to connect: {e}")
        else:
            if st.button("Disconnect"):
                disconnect()

    # --- Question section ---
    st.header("Question")
    q = st.session_state.get("current_question")

    if q:
        st.subheader(q.get("question"))
        remaining = max(0, int(q.get("_deadline_ts", 0) - time.time()))
        total = int(q.get("time", 10))
        progress = (total - remaining) / max(1, total)
        st.progress(progress)
        st.write(f"Time remaining: {remaining}s")

        choice = st.radio("Select an answer:", q.get("choices", []))
        if st.button("Submit Answer"):
            send_answer(q.get("id"), choice)
    else:
        st.write("No active question — wait for the host to start the round.")

    # --- Leaderboard ---
    st.header("Leaderboard")
    render_leaderboard()

    # --- Messages ---
    st.header("Messages")
    for m in st.session_state.get("messages", [])[-10:][::-1]:
        st.write(m)


if __name__ == "__main__":
    main()
    