# 🎯 TCP-Based Kahoot Clone using Streamlit

A real-time, multi-user quiz application inspired by Kahoot — built with Python, Streamlit, and TCP sockets. This project was created as part of a Computer Networks and Design mini-project by a group of four students.

---

## 📌 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [How to Run](#-how-to-run)
- [Team Roles](#-team-roles)
- [Project Structure](#-project-structure)
- [License](#-license)

---

## 🚀 Features

- 🔗 TCP-based connection between a server and multiple clients
- 📺 Interactive Streamlit interface for players
- ⏱ Real-time question broadcast and response handling
- 🧠 Customizable quizzes via JSON files
- 📊 Scoreboard tracking and updates
- 🎉 Gamified UI (progress bars, celebrations, etc.)

---

## 🛠 Tech Stack

- Python 3.10+
- TCP Sockets (`socket`, `threading`)
- Streamlit
- JSON

---

## 🧩 System Architecture

```

```
  [Player Client]      [Player Client]
    |                    |
    |---- TCP Socket ----|
    |        TCP Server        |
    |------------------------>|
       Broadcasts Questions
       Collects Answers
       Calculates Scores
```

````

---

## 📦 Installation

### Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/kahoot-networked-tcp.git
cd kahoot-networked-tcp
````

### Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🧪 How to Run

### 1. Start the server:

Run from the project root so imports and relative paths work correctly:

```bash
# activate your venv first (if you made one at the project root)
source .venv/bin/activate

# start the TCP server (example defaults)
python3 server/tcp_server.py --host 0.0.0.0 --port 8888 --questions questions/sample_questions.json
```

### 2. Run the client (in separate terminals or machines):

From the project root (with the venv activated):

```bash
streamlit run client/streamlit_app.py
```

### 3. Join using IP and port prompted in the UI

---

## 👥 Team Roles

| Name  | Role                            |
| ----- | ------------------------------- |
| Alice | TCP Server & Protocol Logic     |
| Bob   | Streamlit UI + State Handling   |
| Carol | JSON Quiz Manager & Scoreboard  |
| Fares | GitHub, Testing & Documentation |

---

## 📁 Project Structure

```
kahoot-networked-tcp/
├── client/                   # Streamlit-based player UI
│   ├── streamlit_app.py
│   └── assets/
├── server/                   # TCP Server logic
│   └── tcp_server.py
├── shared/                   # Shared utilities
│   └── utils.py
├── questions/                # Quiz questions
│   └── sample_questions.json
├── docs/                     # Design diagrams, slides
├── .gitignore
├── README.md
└── requirements.txt
```

# 🧩 CS411 – Lab 4 Mini Project: TCP Online Quiz Game

**Course:** CS411 — Computer Networks  
**Instructor:** M. Iheb Hergli  
**Team Size:** 4 members  
**Project Type:** Mini project (counts as *two* labs)  
**LAN Ports:** Server `8888` (TCP), Streamlit `8501`  
**Submission:** `lab4.zip` (includes code + 3–5 page report + optional slides)

---

## 🎯 Goal

Implement a **multiplayer quiz game** over **TCP** with a **Streamlit** client, demonstrating:
- reliable, ordered delivery and multi-client synchronization
- server-side timers and **first-correct** scoring
- clean teamwork & engineering practices suitable for a lab demo

---

## 🗺️ System Overview (aligned to your diagrams)

### Actors & Use Cases

- **Client Player**
  - Connect to server
  - Provide unique username
  - Listen for questions
  - Submit answers (within timer)
  - View feedback & score
  - View leaderboard

- **Server Admin**
  - Start a game round
  - Broadcast questions
  - Set time limits (e.g., 30s)
  - Display end-of-round scores

### End-to-End Flow (Sequence)

1. **Game Initialization**
   - Admin starts round
   - Server **broadcasts question**
   - Server **starts timer** (e.g., 30s)

2. **Players Answer**
   - Clients submit answers
   - Server **checks** each answer
   - Only **first correct** earns points for that question

3. **Feedback to Players**
   - Server sends **correct/wrong** result per player
   - Server updates & **broadcasts leaderboard**
   - Loop for next question … until round ends

> The server **never blocks** on a single client; disconnects or slow clients don’t stall the round.

---

## 🧠 Architecture

### Components

- **Server (TCP, port 8888)**
  - Accept loop (main thread)
  - **Client handler threads** (read LD-JSON, enqueue answers)
  - **Coordinator thread** (broadcast Qs, run timers, score, publish feedback/leaderboard)
  - Shared state guarded by locks: `clients`, `scores`, `current_question_id`, `answered_this_q`

- **Client**
  - TCP socket to server
  - Streamlit UI in `app.py` (username, question view, countdown, leaderboard)

### Message Protocol (LD-JSON over TCP)

TCP is a stream; messages are **newline-delimited JSON** (UTF-8):

```json
{"type":"join","username":"fares"}
{"type":"question","id":7,"text":"Which port is HTTPS?","options":["80","21","25","443"],"deadline_ms":30000}
{"type":"answer","username":"fares","question_id":7,"answer":"443","ts":1730}
{"type":"feedback","username":"fares","correct":true}
{"type":"score","leaderboard":[["fares",3],["ines",2],["youssef",1]]}
{"type":"broadcast","message":"Time is up! Correct answer: 443"}
{"type":"error","code":"BAD_FORMAT","detail":"missing field 'answer'"}


## 🗂️ Repository Structure

```

quiznet-tcp-udp/
├─ tcp_quiz/
│  ├─ server_tcp.py
│  └─ client_tcp.py
├─ app.py                # Streamlit GUI (talks to server via TCP)
├─ questions.txt         # 10 original transport-layer questions
├─ report.pdf            # 3–5 pages
└─ slides.pdf            # optional

````

> Your lab brief also mentions a UDP variant; this README focuses on **TCP + Streamlit** as requested. Keep the above tree if you later add `udp_quiz/` for comparison. :contentReference[oaicite:5]{index=5}

---

## 🧠 System Design

### High-Level Architecture
- **Server (TCP, port 8888)**  
  - Accepts clients; spawns **one thread per client**.  
  - Broadcasts questions; enforces **per-question deadline** (e.g., 30s).  
  - Scores **first correct** answer; broadcasts leaderboard.  
  - Handles malformed input and disconnects gracefully. :contentReference[oaicite:6]{index=6}

- **Client (TCP) + Streamlit GUI (port 8501)**  
  - Connects with a **unique username**.  
  - Displays question + options + countdown.  
  - Sends answer; shows correctness and leaderboard. :contentReference[oaicite:7]{index=7}

### Message Format (JSON over TCP)
All frames are **newline-delimited JSON** (LD-JSON) to preserve message boundaries:

```json
{"type":"join","username":"fares"}
{"type":"question","id":3,"text":"Default TCP port for HTTP?","options":["80","8080","21","25"],"deadline_ms":30000}
{"type":"answer","username":"fares","question_id":3,"answer":"80","ts":1730}
{"type":"score","leaderboard":[["fares",3],["ines",2],["youssef",1]]}
{"type":"broadcast","message":"Time is up! Correct: 80"}
{"type":"ack","ok":true}
{"type":"error","code":"BAD_FORMAT","detail":"Missing field 'answer'"}
````

**Why LD-JSON?**

* TCP is a stream; **newline** acts as a clear delimiter.
* JSON is human-readable, UTF-8, and easy to debug. 

---

## ⚙️ Setup

```bash
# 1) Clone & enter
git clone <your_repo_url> quiznet-tcp-udp
cd quiznet-tcp-udp

# 2) Python env
python3 -m venv venv
source venv/bin/activate

# 3) Deps
pip install streamlit
# (Add more deps if you use logging/typing extras)

# 4) Author questions
cp sample_questions.txt questions.txt   # or create your own 10 Qs
```

> Work on the **same LAN** (Wi-Fi or wired). Open ports **8888** and **8501** in your OS firewall if needed. Remote work is not permitted per lab rules. 

---

## ▶️ Running

**Terminal 1 – Server**

```bash
cd tcp_quiz
python server_tcp.py --host 0.0.0.0 --port 8888 --questions ../questions.txt --qtime 30
```

**Terminal 2..N – Clients (CLI for debugging)**

```bash
cd tcp_quiz
python client_tcp.py --host <SERVER_LAN_IP> --port 8888 --username <name>
```

**Streamlit GUI**

```bash
streamlit run app.py   # opens http://localhost:8501 (or http://<LAN IP>:8501)
```

---

## 🧩 Core Game Logic

1. **Join**: client sends `join` → server registers username.
2. **Broadcast question**: includes `deadline_ms`.
3. **Answer window**: server accepts answers; **first correct** gets points.
4. **Timeout**: server reveals correct answer; emits `score`.
5. **Round advance**: repeat for 5–10 questions; end with final leaderboard. 

---

## 🧵 Concurrency & Reliability (TCP)

* **Server**

  * Main thread: `accept()` loop.
  * Client handler thread: read LD-JSON, validate, enqueue answers.
  * **Coordinator** (server control thread): broadcasts questions, times deadlines, awards points, publishes scores.
* **Thread Safety**

  * Guard shared state (`clients`, `scores`, `current_question_id`, `answered`) with `threading.Lock()`.
* **Backpressure & Robustness**

  * Non-blocking send with short timeouts; if a client is slow, **skip** rather than stall the round.
  * On socket error: **remove client**, continue the game. 

---

## 🧪 Test Plan (what to screenshot / record)

| Scenario             | Steps                         | Expected                             |
| -------------------- | ----------------------------- | ------------------------------------ |
| Normal operation     | 1 server + 3 clients + GUI    | All receive Qs, scoring works        |
| Simultaneous correct | 2 clients answer same correct | Only **first** earns points          |
| Timeout              | Don’t answer                  | Server reveals correct answer        |
| Client disconnect    | Kill one client mid-round     | Others continue uninterrupted        |
| GUI end-to-end       | Use Streamlit only            | Full flow works, leaderboard updates |

> Include these in your **report** with brief commentary. 

---

## 👥 Team Organization (4 members)

| Role                         | Main Duties                                                    |
| ---------------------------- | -------------------------------------------------------------- |
| **Lead & Release Manager**   | Plan, milestones, PR gatekeeper, demo orchestration            |
| **Backend Engineer**         | `server_tcp.py`, timers, scoring, broadcasts                   |
| **Client/Protocol Engineer** | `client_tcp.py`, message framing, error handling               |
| **GUI & QA Engineer**        | `app.py`, UX, multi-client tests, screenshots, report assembly |

> Rotate small tasks weekly so everyone touches server, client, and GUI.

---

## 🧭 Milestones & Timeline

| Week                         | Milestone                                           | Output                             |
| ---------------------------- | --------------------------------------------------- | ---------------------------------- |
| **Week 8 (Design)**          | Architecture, data format, state machine, diagrams  | Architecture diagram; protocol doc |
| **Week 9 (Build)**           | Multithreaded TCP server; CLI client; Streamlit GUI | Working TCP + GUI                  |
| **Week 10 (Test & Present)** | Full test matrix; report; slides; demo              | `lab4.zip` + live demo             |

> Follow the lab’s Week 8–10 cadence and deliverables. 

---

## 🧾 Deliverables & Grading

**Deliverables (final zip):** `server_tcp.py`, `client_tcp.py`, `app.py`, `questions.txt`, `report.pdf`, `slides.pdf (optional)` — submitted as `lab4.zip`. 

**Grading (100%)**

* **Functionality (TCP + GUI)** — 40%
* **Code Quality & Best Practices** — 20%
* **Report Documentation (3–5 pages)** — 20%
* **Presentation & Demo** — 20%
* **Bonus** (creative extensions) — up to +5%

**Report outline (3–5 pages)**

* Intro; Architecture; Workflow & Implementation; TCP vs (briefly) UDP comparison; Challenges; Individual Contributions; Conclusion; References.

---

## 🧑‍💻 Git Workflow & Communication

### Branching

```
main           # protected, tagged releases only
dev            # integration branch
feature/server
feature/client
feature/gui
docs/report
```

### PR Policy

* Small, focused PRs; **1 reviewer minimum**; squash & merge.
* Commit messages (Conventional Commits):

  * `feat: add LD-JSON framing`
  * `fix: handle client disconnect`
  * `refactor: extract broadcast util`
  * `docs: add sequence diagram`

### Issue Tracking

* Use GitHub Projects or Issues with labels: `server`, `client`, `gui`, `bug`, `test`, `docs`, `priority`.

### Sync Rhythm

* **15-min daily stand-up** (async in chat if needed).
* **Mid-week integration test** on LAN.
* **End-week demo rehearsal**.

---

## ✅ Best Practices Checklist

* **Networking**

  * Use **newline-delimited JSON**; validate fields.
  * Set socket timeouts; catch `ConnectionResetError`, `BrokenPipeError`.
* **Timing & Scoring**

  * Server-side authoritative timer; ignore late answers.
  * Track **first-correct** via an atomic flag/lock.
* **Threading**

  * Shared structures behind locks; avoid long holds.
  * Never block the coordinator on a single slow client send.
* **GUI**

  * Keep socket I/O off the main Streamlit thread (thread or async wrapper).
  * Use `st.session_state` for username, connection, and last leaderboard.
* **Code Quality**

  * PEP8, type hints, docstrings for public functions.
  * Centralize constants (`PORT`, `QTIME`, message keys).
* **Observability**

  * Structured logs: `INFO` (joins, broadcasts), `WARN` (slow client), `ERROR` (disconnects).
  * Debug flag to dump wire messages when needed.
* **Data**

  * Externalize `questions.txt`; validate it at server start.

---

## 🧪 Quick Self-Test (before submission)

* [ ] 3 clients + GUI can join and play a full round
* [ ] First-correct scoring proven with simultaneous answers
* [ ] Timeout reveals correct answer and advances round
* [ ] Disconnect doesn’t crash server or stall round
* [ ] Screenshots for all scenarios added to `report.pdf`
* [ ] Ports 8888 and 8501 open; LAN IPs confirmed
* [ ] `lab4.zip` contains all required files

---

## 🎁 Bonus Ideas (+5%)

* Per-question **countdown UI** with progress bar.
* **Chat** broadcast channel.
* Persistent **leaderboard history** (JSON/CSV).
* Simple **auth** or nickname reservation.

---

## 🔐 Academic Integrity

All work must be **original**; discussion allowed, but **no identical code**. Include **individual contributions** in the report; absence on demo day penalizes grade (÷2). 

---

## 🙏 Acknowledgment

This README aligns with the **CS411 Lab 4** instructions (Mediterranean Institute of Technology) for weeks 8–10, deliverables, ports, GUI requirement, grading, and test scenarios. 

```

If you want, I can also generate minimal, production-ready **starter templates** for `server_tcp.py`, `client_tcp.py`, and `app.py` that follow this roadmap (LD-JSON framing, locks, timers, and a clean Streamlit layout).
```
