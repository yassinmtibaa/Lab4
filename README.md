Sure ✅ — here’s the **complete, ready-to-save** `README.md` version in Markdown code format:

````markdown
# 🎯 TCP-Based Kahoot Clone using Streamlit

A real-time, multi-user quiz game inspired by **Kahoot**, built using **Python**, **Streamlit**, and **TCP sockets**.  
Developed as part of the **CS411 Computer Networks and Design** mini-project by a team of four students.

---

## 📌 Table of Contents
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [How to Run](#-how-to-run)
- [Team Roles](#-team-roles)
- [Project Structure](#-project-structure)
- [Lab Context](#-cs411--lab-4-mini-project-tcp-online-quiz-game)
- [Best Practices](#-best-practices-checklist)
- [Grading](#-deliverables--grading)

---

## 🚀 Features
- 🔗 **Real-time multiplayer** quiz over TCP sockets  
- 🧠 **Customizable question sets** via JSON  
- 📺 **Interactive Streamlit UI** for players  
- 🧾 **Server-side scoring** with “first correct” logic  
- 📊 **Live leaderboard** updates  
- ⏱ **Timed rounds** with progress indicators  
- 💬 Robust communication protocol (LD-JSON over TCP)

---

## 🛠 Tech Stack
- **Language:** Python 3.10+
- **Networking:** TCP sockets, threading
- **Frontend:** Streamlit
- **Data Format:** JSON (newline-delimited for TCP framing)

---

## 🧩 System Architecture

```text
  [ Player 1 ]      [ Player 2 ]       [ Player 3 ]
       |                 |                  |
       |---- TCP Socket ---- TCP Socket ----|
                     |
              [ TCP Quiz Server ]
                     |
          -----------------------------
          | Broadcast Questions & Scores |
          -----------------------------
````

---

## 📦 Installation

### Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/kahoot-networked-tcp.git
cd kahoot-networked-tcp
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🧪 How to Run

### 1️⃣ Start the Server

Run from the **project root** (so imports work correctly):

```bash
# activate your virtual environment
source .venv/bin/activate

# start the TCP server
python3 -m server.tcp_server --host 0.0.0.0 --port 8888 --questions questions/sample_questions.json
```

You’ll see:

```
Waiting for players to connect...
Type 'start' and press Enter to begin the quiz.
```

### 2️⃣ Start the Client(s)

In another terminal (or different machine on the same LAN):

```bash
streamlit run client/streamlit_app.py
```

Enter the **server IP** and **port 8888**, then click **Connect**.

---

## 👥 Team Roles

| Name  | Role                          |
| ----- | ----------------------------- |
| Alice | TCP Server & Protocol Design  |
| Bob   | Streamlit UI & Client Logic   |
| Carol | Question Management & Testing |
| Fares | Debugging, Documentation, QA  |

---

## 📁 Project Structure

```text
kahoot-networked-tcp/
├── client/
│   └── streamlit_app.py          # Streamlit player interface
├── server/
│   └── tcp_server.py             # Multi-threaded TCP server
├── shared/
│   └── utils.py                  # LD-JSON send/receive utilities
├── questions/
│   └── sample_questions.json     # Example quiz file
├── README.md
└── requirements.txt
```

---

# 🧩 CS411 – Lab 4 Mini Project: TCP Online Quiz Game

**Course:** CS411 — Computer Networks
**Instructor:** *M. Iheb Hergli*
**Team Size:** 4 members
**LAN Ports:** Server `8888`, Streamlit `8501`
**Submission:** `lab4.zip` (code + report + optional slides)

---

## 🎯 Goal

Implement a **multiplayer quiz game** using **TCP** and a **Streamlit** UI, demonstrating:

* Ordered and reliable delivery over TCP
* Thread-safe multi-client management
* Real-time updates (first-correct scoring, leaderboards)

---

## 🧠 Architecture Summary

### Server

* Multi-threaded TCP server handling multiple clients
* Broadcasts questions and score updates
* Awards **only the first correct** answer per round
* Thread-safe state management using locks

### Client

* Streamlit app with live progress and countdown timers
* Connects via TCP to the quiz server
* Displays questions, accepts answers, shows leaderboard

### Communication Protocol

All messages are **newline-delimited JSON** (LD-JSON):

```json
{"type":"join","username":"fares"}
{"type":"question","id":1,"question":"Which port is HTTPS?","choices":["80","443"],"time":10}
{"type":"answer","username":"fares","question_id":1,"answer":"443"}
{"type":"feedback","correct":true}
{"type":"score","scores":{"fares":1}}
```

---

## 🧪 Test Scenarios

| Test Case                    | Expected Result                             |
| ---------------------------- | ------------------------------------------- |
| 3 clients join               | All registered, welcome messages shown      |
| One correct answer           | Only first correct gains point              |
| Timeout (no answers)         | Server reveals correct answer automatically |
| Client disconnects mid-round | Game continues unaffected                   |
| Streamlit refresh            | UI updates every second (via autorefresh)   |

---

## 🧾 Deliverables & Grading

| Criteria                      | Weight |
| ----------------------------- | -----: |
| Functionality (TCP + GUI)     |    40% |
| Code Quality & Best Practices |    20% |
| Report Documentation (3–5 pp) |    20% |
| Presentation & Demo           |    20% |
| **Bonus (creative features)** |    +5% |

---

## ✅ Best Practices Checklist

* [x] Use newline-delimited JSON for clear framing
* [x] Handle broken sockets and timeouts gracefully
* [x] Server remains responsive during client disconnects
* [x] Locks protect shared state (`scores`, `clients`)
* [x] Streamlit client uses background thread for network I/O
* [x] Code follows PEP8 + type hints
* [x] Works across multiple machines on the same LAN

---

## 🏁 Status

✅ **Completed:** TCP server, Streamlit client, and JSON protocol
🐞 **Known Issues:** Minor UI flicker (Streamlit reruns), occasional reconnect delay
🎯 **Next Step:** Optional UDP version (for comparison, not required)

---

## 🙏 Acknowledgments

This project was built following the **CS411 Lab 4** requirements at
**Mediterranean Institute of Technology (SMU)**, supervised by **M. Iheb Hergli**.
Special thanks to the teaching staff for guidance and feedback.

