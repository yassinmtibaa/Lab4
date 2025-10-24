# 🎮 TCP Kahoot - Multiplayer Quiz Game

**CS411 Computer Networks Project**  
*Mediterranean Institute of Technology (SMU)*  
*Instructor: M. Iheb Hergli*

---

## 📖 Overview

A real-time multiplayer quiz game built with **TCP sockets**, **Python threading**, and **Streamlit**. Demonstrates reliable network communication, concurrency, and synchronization concepts from the Computer Networks course.

### Key Features
- ✅ **Multithreaded TCP Server** - Handles multiple clients concurrently
- ✅ **Real-time Gameplay** - Synchronized question distribution and scoring
- ✅ **First-Correct Bonus** - Awards extra points to fastest correct answer
- ✅ **Live Leaderboard** - Real-time score tracking and rankings
- ✅ **Thread-Safe State** - Protected with `threading.Lock()`
- ✅ **LD-JSON Protocol** - Newline-delimited JSON for message framing
- ✅ **Interactive UI** - Built with Streamlit for smooth user experience

---

## 🏗️ Architecture

```
┌─────────────────┐         TCP/IP          ┌─────────────────┐
│  Streamlit UI   │◄─────────────────────────►│   TCP Server    │
│   (Client 1)    │     Port 8888 (LD-JSON)  │  (tcp_server.py)│
└─────────────────┘                          │                 │
                                             │  ┌───────────┐  │
┌─────────────────┐         TCP/IP          │  │ Thread 1  │  │
│  Streamlit UI   │◄─────────────────────────►│ ├───────────┤  │
│   (Client 2)    │     Port 8888           │  │ Thread 2  │  │
└─────────────────┘                          │  ├───────────┤  │
                                             │  │ Thread N  │  │
┌─────────────────┐         TCP/IP          │  └───────────┘  │
│  Streamlit UI   │◄─────────────────────────►│                 │
│   (Client N)    │     Port 8888           │  Shared State   │
└─────────────────┘                          │  (Thread-Safe)  │
                                             └─────────────────┘
```

### Components

1. **`server/tcp_server.py`** - Multithreaded TCP server
   - Listens on port 8888
   - Thread-per-client concurrency model
   - Broadcasts questions and leaderboard updates
   - Thread-safe score management with locks

2. **`client/streamlit_app.py`** - Interactive web-based client
   - Connects to server via TCP
   - Background listener thread for async message handling
   - Real-time UI updates with Streamlit
   - Thread-safe message queue

3. **`shared/utils.py`** - Protocol utilities
   - `send_json()` - Serialize and send JSON with newline delimiter
   - `recv_json()` - Receive and parse newline-delimited JSON
   - Handles partial reads and buffering

4. **`questions/sample_questions.json`** - Quiz data
   - 10 Computer Networks questions
   - Multiple choice format with correct answer index

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Clone/Extract Project
```bash
cd tcp-kahoot
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Verify Structure
```
tcp-kahoot/
├── server/
│   └── tcp_server.py
├── client/
│   └── streamlit_app.py
├── shared/
│   └── utils.py
├── questions/
│   └── sample_questions.json
├── README.md
└── requirements.txt
```

---

## 🎮 Running the Game

### Start Server (Terminal 1)
```bash
cd tcp-kahoot
python server/tcp_server.py
```

Expected output:
```
==================================================
   TCP Kahoot Server - CS411 Project
   Mediterranean Institute of Technology
==================================================
[INFO] Loaded 10 questions
[INFO] Server started on 0.0.0.0:8888
[INFO] Waiting for clients...
```

### Start Client(s) (Terminal 2, 3, ...)
```bash
cd tcp-kahoot
streamlit run client/streamlit_app.py
```

The Streamlit UI will open automatically in your browser at `http://localhost:8501`

### Gameplay Steps

1. **Connect**
   - Enter server IP (use `localhost` for local testing)
   - Enter port `8888`
   - Enter your player name
   - Click "Connect"

2. **Wait for Players**
   - Multiple players can join
   - Any player can click "Start Game" (admin control)

3. **Answer Questions**
   - Read the question (20 seconds per question)
   - Click one of the four colored answer buttons
   - Faster correct answers earn bonus points!
   - First correct answer gets +100 bonus points

4. **View Results**
   - See live leaderboard after each question
   - Final results show podium (1st, 2nd, 3rd place)
   - Play again or disconnect

---

## 🔧 Protocol Specification

### Message Format
All messages use **newline-delimited JSON (LD-JSON)**:
```
{"type": "message_type", "data": "..."}\n
```

### Client → Server Messages

**Registration:**
```json
{"type": "register", "name": "PlayerName"}
```

**Answer Submission:**
```json
{"type": "answer", "answer": 2}
```

**Start Game (Admin):**
```json
{"type": "start_game"}
```

### Server → Client Messages

**Registration Confirmation:**
```json
{"type": "registered", "name": "PlayerName", "message": "Successfully registered!"}
```

**Question Broadcast:**
```json
{
  "type": "question",
  "question_number": 1,
  "total_questions": 10,
  "question": "What does TCP stand for?",
  "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
  "time_limit": 20
}
```

**Answer Result:**
```json
{
  "type": "answer_result",
  "correct": true,
  "points": 150,
  "message": "Correct! +150 points (First correct +100!)"
}
```

**Leaderboard Update:**
```json
{
  "type": "leaderboard",
  "leaderboard": [
    {"name": "Player1", "score": 450},
    {"name": "Player2", "score": 300}
  ]
}
```

**Game Over:**
```json
{
  "type": "game_over",
  "leaderboard": [...],
  "message": "Game Over! Thanks for playing!"
}
```

---

## 🧵 Threading & Concurrency

### Server Threading Model

```python
# Main thread: Accept connections
while True:
    client_socket, address = server_socket.accept()
    
    # Spawn thread per client
    thread = threading.Thread(target=handle_client, args=(client_socket,))
    thread.start()

# Shared state protection
lock = threading.Lock()

def update_score(player, points):
    with lock:  # Critical section
        players[player]["score"] += points
```

### Client Threading Model

```python
# Main thread: Streamlit UI
def main():
    render_ui()
    process_message_queue()

# Background thread: Socket listener
def listener_thread(socket, queue):
    while True:
        message = recv_json(socket)
        queue.put(message)  # Thread-safe queue
```

---

## 🔐 Thread Safety Mechanisms

### 1. Server State Protection
```python
self.lock = threading.Lock()

with self.lock:
    # Critical section - only one thread executes this
    self.clients[socket]["score"] += points
```

### 2. Client Message Queue
```python
message_queue = queue.Queue()  # Thread-safe FIFO

# Listener thread (writes)
message_queue.put(server_message)

# UI thread (reads)
message = message_queue.get_nowait()
```

### 3. Broadcast Synchronization
```python
def broadcast(self, message):
    with self.lock:
        for client_socket in self.clients:
            send_json(client_socket, message)
```

---

## 📊 Scoring System

| Event | Points |
|-------|--------|
| Correct Answer (Base) | 100 |
| Speed Bonus | 0-50 (based on time remaining) |
| First Correct Answer | +100 bonus |
| Wrong Answer | 0 |

**Formula:**
```python
points = base_points + time_bonus + first_bonus
time_bonus = int((20 - elapsed_time) / 20 * 50)
first_bonus = 100 if first_correct else 0
```

**Example:**
- Answer correctly in 5 seconds: `100 + 37 + 0 = 137 points`
- First person to answer correctly in 3 seconds: `100 + 42 + 100 = 242 points`

---

## 🐛 Troubleshooting

### Server Issues

**Problem:** `Address already in use`
```bash
# Kill existing process on port 8888
lsof -ti:8888 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8888   # Windows
```

**Problem:** Clients can't connect
- Check firewall settings
- Ensure server is running (`0.0.0.0:8888`)
- Use correct IP address (use `ifconfig` or `ipconfig`)

### Client Issues

**Problem:** Streamlit won't start
```bash
pip install --upgrade streamlit
streamlit run client/streamlit_app.py --server.port 8502  # Use different port
```

**Problem:** Connection refused
- Verify server is running
- Check IP address and port
- Test with `telnet localhost 8888`

### Network Issues

**Problem:** Messages not received
- Check `recv_json()` buffer size
- Verify JSON has newline delimiter
- Look for socket timeout errors

---

## 🧪 Testing Guide

### Unit Testing

**Test JSON Framing:**
```python
from shared.utils import send_json, recv_json

# Create socket pair for testing
import socket
s1, s2 = socket.socketpair()

# Test send/receive
send_json(s1, {"type": "test", "data": 123})
msg = recv_json(s2)
assert msg["type"] == "test"
```

### Integration Testing

1. **Single Client Test**
   - Start server
   - Connect one client
   - Start game
   - Answer all questions
   - Verify final score

2. **Multi-Client Test**
   - Start server
   - Connect 3+ clients
   - Start game from one client
   - All clients answer questions
   - Verify leaderboard consistency

3. **Stress Test**
   - Connect 10+ clients simultaneously
   - Check for race conditions
   - Monitor server CPU/memory usage

### Edge Cases

- Client disconnects mid-game
- Answer submitted after time expires
- Multiple clients answer simultaneously
- Server restart with connected clients
- Invalid JSON messages

---

## 📈 Performance Considerations

### Server Optimization
- **Thread Pool:** Consider using `concurrent.futures.ThreadPoolExecutor` for better thread management
- **Keep-Alive:** Add periodic heartbeat messages to detect dead connections
- **Buffer Size:** Tune `recv()` buffer size based on message sizes

### Client Optimization
- **Message Batching:** Process multiple queued messages per UI refresh
- **Auto-Reconnect:** Implement reconnection logic with exponential backoff
- **Timeout Handling:** Set appropriate socket timeouts (e.g., 30 seconds)

---

## 📚 Networking Concepts Demonstrated

### 1. TCP Stream vs. Datagram
- TCP provides **reliable, ordered, stream-based** communication
- Requires message framing (LD-JSON) to identify message boundaries

### 2. Concurrency Models
- **Thread-per-client** model for server scalability
- Alternative: Event-driven (asyncio) or process-based (multiprocessing)

### 3. Socket Programming
- `socket.socket()` - Create endpoint
- `bind()` / `listen()` / `accept()` - Server operations
- `connect()` / `send()` / `recv()` - Client operations

### 4. Synchronization
- **Mutex locks** prevent race conditions on shared state
- **Thread-safe queues** enable inter-thread communication

### 5. Protocol Design
- **Message types** define communication semantics
- **State machines** coordinate client-server interaction
- **Error handling** ensures robustness

---

## 🎓 Learning Outcomes

By completing this project, students understand:

1. **TCP Socket Programming**
   - Client-server architecture
   - Connection establishment and teardown
   - Reliable data transfer

2. **Concurrency & Threading**
   - Multi-threaded server design
   - Race conditions and synchronization
   - Thread-safe data structures

3. **Protocol Design**
   - Message framing techniques
   - State management
   - Error handling strategies

4. **Application Integration**
   - Combining networking with UI frameworks
   - Asynchronous message handling
   - Real-time communication

---

## 👥 Team Contributions

| Member | Role | Responsibilities |
|--------|------|------------------|
| Member 1 | Server Developer | `tcp_server.py`, threading, state management |
| Member 2 | Client Developer | `streamlit_app.py`, UI design, listener thread |
| Member 3 | Protocol Designer | `utils.py`, message formats, testing |
| Member 4 | Documentation | README, report, diagrams |

---

## 📝 Report Structure

### Suggested Outline (3-5 pages)

1. **Introduction** (0.5 pages)
   - Project goals
   - TCP relevance to Computer Networks

2. **Architecture** (1 page)
   - Component diagram
   - Threading model
   - Data flow

3. **Protocol Design** (1 page)
   - Message format (LD-JSON)
   - Message types
   - State machine diagram

4. **Implementation** (1.5 pages)
   - Key algorithms (broadcasting, scoring)
   - Thread safety mechanisms
   - Code snippets with explanations

5. **Testing & Results** (0.5 pages)
   - Test scenarios
   - Screenshots
   - Performance observations

6. **Conclusion** (0.5 pages)
   - Challenges encountered
   - Solutions implemented
   - Key learnings

---

## 🔗 References

- [Python Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html)
- [Python Threading Documentation](https://docs.python.org/3/library/threading.html)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [TCP/IP Protocol Suite (Forouzan)](https://www.mheducation.com/)
- [Computer Networking: A Top-Down Approach (Kurose & Ross)](https://gaia.cs.umass.edu/kurose_ross/)

---

## 📄 License

This project is developed for educational purposes as part of CS411 coursework at Mediterranean Institute of Technology (SMU).

---

## 🙏 Acknowledgments

- **Instructor:** M. Iheb Hergli
- **Course:** CS411 - Computer Networks
- **Institution:** Mediterranean Institute of Technology (SMU)

---

**Questions or Issues?** Contact your team members or instructor.

**Last Updated:** January 2025