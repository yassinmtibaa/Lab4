"""Improved Streamlit client interface for the TCP Quiz.

Features:
- Player name and connect button
- Incoming message area
- Current question with countdown timer
- Submit answer and local scoreboard

Notes: This example keeps a simple local scoreboard and assumes the server will
broadcast question messages as newline-delimited JSON.
"""
import streamlit as st
import socket
import threading
import time
from collections import defaultdict

from shared.utils import send_json, recv_json


st.set_page_config(page_title="Kahoot TCP Client", layout="centered")
st.title("Kahoot TCP — Player Client")


def receiver_loop(sock):
    """Background thread: receive messages and push into session_state queues."""
    while True:
        msg = recv_json(sock)
        if msg is None:
            # connection closed
            st.session_state.connected = False
            break
        t = msg.get("type")
        if t == "question":
            st.session_state.incoming.append(msg)
        elif t == "ack":
            st.session_state.incoming.append({"type": "system", "text": f"Server ack q:{msg.get('question_id')}"})


def connect(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    st.session_state.sock = sock
    st.session_state.connected = True
    st.session_state.incoming = []
    threading.Thread(target=receiver_loop, args=(sock,), daemon=True).start()


if "connected" not in st.session_state:
    st.session_state.connected = False
if "incoming" not in st.session_state:
    st.session_state.incoming = []
if "scoreboard" not in st.session_state:
    st.session_state.scoreboard = defaultdict(int)


with st.sidebar:
    st.header("Player")
    name = st.text_input("Player name", value=st.session_state.get("name", "player1"))
    st.session_state["name"] = name
    host = st.text_input("Server host", value="127.0.0.1")
    port = st.number_input("Server port", value=5001)
    if not st.session_state.connected:
        if st.button("Connect to server"):
            try:
                connect(host, int(port))
                st.sidebar.success("Connected")
            except Exception as e:
                st.sidebar.error(f"Failed to connect: {e}")
    else:
        if st.button("Disconnect"):
            try:
                st.session_state.sock.close()
            except Exception:
                pass
            st.session_state.connected = False


st.write("## Messages")
msg_box = st.empty()
for m in st.session_state.incoming[-5:]:
    if m.get("type") == "question":
        msg_box.info(f"Question incoming: {m.get('id')} - {m.get('question')}")
    elif m.get("type") == "system":
        msg_box.write(f"SYSTEM: {m.get('text')}")
    else:
        msg_box.write(str(m))


st.write("## Current Question")
if st.session_state.incoming:
    q = None
    # find the most recent question
    for m in reversed(st.session_state.incoming):
        if m.get("type") == "question":
            q = m
            break
    if q:
        st.subheader(q.get("question"))
        choices = q.get("choices", [])
        # simple client-side countdown
        remaining = q.get("time", 10)
        start_time = st.session_state.get("q_start_" + str(q.get("id")))
        if start_time is None:
            st.session_state["q_start_" + str(q.get("id"))] = time.time()
            start_time = st.session_state["q_start_" + str(q.get("id"))]

        elapsed = int(time.time() - start_time)
        left = max(0, remaining - elapsed)
        st.progress((remaining - left) / max(1, remaining))
        st.write(f"Time left: {left}s")

        choice = st.radio("Select an answer", list(range(len(choices))), format_func=lambda i: choices[i])
        if st.button("Submit Answer"):
            if st.session_state.connected:
                send_json(st.session_state.sock, {"type": "answer", "client_id": st.session_state["name"], "question_id": q.get("id"), "choice": int(choice)})
                st.success("Answer sent")
            else:
                st.error("Not connected to server")
else:
    st.info("Waiting for questions from server...")


st.write("## Local Scoreboard")
for player, sc in st.session_state.scoreboard.items():
    st.write(f"{player}: {sc}")

