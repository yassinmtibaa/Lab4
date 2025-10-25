"""
Streamlit TCP Kahoot Client - CS411 Computer Networks Project
Interactive UI with background listener thread for server messages.
"""

import streamlit as st
import socket
import threading
import queue
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.utils import send_json, recv_json, close_socket_safe


# Compatibility wrapper for rerun across Streamlit versions
def rerun():
    """Wrapper for st.rerun() that works across all Streamlit versions"""
    if hasattr(st, 'rerun'):
        st.rerun()
    elif hasattr(st, 'experimental_rerun'):
        st.experimental_rerun()
    else:
        raise RuntimeError("No rerun method available in this Streamlit version")


# Page configuration
st.set_page_config(
    page_title="TCP Kahoot Client",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
    }
    .success-box { background-color: #d4edda; color: #155724; }
    .error-box { background-color: #f8d7da; color: #721c24; }
    .info-box { background-color: #d1ecf1; color: #0c5460; }
    .question-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        font-size: 1.5rem;
        text-align: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.connected = False
        st.session_state.socket = None
        st.session_state.listener_thread = None
        st.session_state.message_queue = queue.Queue()
        st.session_state.player_name = ""
        st.session_state.score = 0
        st.session_state.current_question = None
        st.session_state.answered = False
        st.session_state.leaderboard = []
        st.session_state.game_state = "waiting"
        st.session_state.status_message = ""
        st.session_state.answer_result = None
        st.session_state.time_left = 20
        st.session_state.question_number = 0
        st.session_state.total_questions = 0
        st.session_state.last_update = time.time()
        st.session_state.force_refresh = False

init_session_state()


def listener_thread(sock, msg_queue):
    """
    Background thread that listens for server messages.
    Puts messages into a queue for the main thread to process.
    """
    print("[LISTENER] Thread started")
    try:
        while True:
            print("[LISTENER] Waiting for message...")
            msg = recv_json(sock)
            
            if msg is None:
                # Server disconnected
                print("[LISTENER] Server disconnected (recv returned None)")
                msg_queue.put({"type": "disconnected"})
                break
            
            print(f"[LISTENER] Received: {msg.get('type')}")
            msg_queue.put(msg)
    
    except Exception as e:
        print(f"[ERROR] Listener thread error: {e}")
        import traceback
        traceback.print_exc()
        msg_queue.put({"type": "error", "message": str(e)})


def connect_to_server(host, port, player_name):
    """Connect to TCP server and start listener thread."""
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # Timeout only for initial connection
        sock.connect((host, port))
        
        # Register player
        send_json(sock, {
            "type": "register",
            "name": player_name
        })
        
        # Wait for registration confirmation
        response = recv_json(sock)
        
        if response and response.get('type') == 'registered':
            # Remove timeout for ongoing communication
            sock.settimeout(None)
            
            st.session_state.socket = sock
            st.session_state.player_name = player_name
            st.session_state.connected = True
            
            print(f"[CLIENT] Connected successfully as {player_name}")
            
            # Start listener thread
            listener = threading.Thread(
                target=listener_thread,
                args=(sock, st.session_state.message_queue),
                daemon=True
            )
            listener.start()
            st.session_state.listener_thread = listener
            
            print("[CLIENT] Listener thread started")
            
            return True, "Connected successfully!"
        else:
            close_socket_safe(sock)
            return False, "Registration failed"
    
    except socket.timeout:
        return False, "Connection timeout - check server address"
    except ConnectionRefusedError:
        return False, "Connection refused - is server running?"
    except Exception as e:
        return False, f"Connection error: {e}"


def disconnect_from_server():
    """Disconnect from server and cleanup."""
    if st.session_state.socket:
        close_socket_safe(st.session_state.socket)
    
    st.session_state.connected = False
    st.session_state.socket = None
    st.session_state.game_state = "waiting"
    st.session_state.current_question = None
    st.session_state.score = 0


def process_messages():
    """Process all pending messages from the server."""
    messages_processed = 0
    needs_rerun = False
    
    while not st.session_state.message_queue.empty() and messages_processed < 10:
        try:
            msg = st.session_state.message_queue.get_nowait()
            if handle_server_message(msg):
                needs_rerun = True
            messages_processed += 1
        except queue.Empty:
            break
    
    return needs_rerun


def handle_server_message(msg):
    """Handle individual server message and update session state."""
    msg_type = msg.get('type')
    
    # Debug: Print received messages
    print(f"[CLIENT DEBUG] Received message: {msg_type}")
    print(f"[CLIENT DEBUG] Full message: {msg}")
    
    if msg_type == 'waiting':
        st.session_state.status_message = msg.get('message', '')
        st.session_state.game_state = "waiting"
        st.session_state.force_refresh = True
    
    elif msg_type == 'game_started':
        st.session_state.game_state = "playing"
        st.session_state.total_questions = msg.get('total_questions', 0)
        st.session_state.status_message = "Game starting..."
        st.session_state.force_refresh = True
    
    elif msg_type == 'question':
        print(f"[CLIENT DEBUG] Processing question: {msg.get('question')}")
        st.session_state.current_question = {
            'question': msg.get('question'),
            'options': msg.get('options'),
            'time_limit': msg.get('time_limit', 20)
        }
        st.session_state.question_number = msg.get('question_number', 0)
        st.session_state.total_questions = msg.get('total_questions', 0)
        st.session_state.answered = False
        st.session_state.answer_result = None
        st.session_state.time_left = msg.get('time_limit', 20)
        st.session_state.game_state = "playing"
        st.session_state.force_refresh = True
        print(f"[CLIENT DEBUG] Game state set to: {st.session_state.game_state}")
        print(f"[CLIENT DEBUG] Current question stored: {st.session_state.current_question}")
    
    elif msg_type == 'answer_result':
        st.session_state.answered = True
        st.session_state.answer_result = {
            'correct': msg.get('correct'),
            'points': msg.get('points', 0),
            'message': msg.get('message', '')
        }
        if msg.get('correct'):
            st.session_state.score += msg.get('points', 0)
        st.session_state.force_refresh = True
    
    elif msg_type == 'answer_reveal':
        st.session_state.status_message = msg.get('explanation', '')
        st.session_state.force_refresh = True
    
    elif msg_type == 'leaderboard':
        st.session_state.leaderboard = msg.get('leaderboard', [])
        st.session_state.force_refresh = True
    
    elif msg_type == 'game_over':
        st.session_state.game_state = "results"
        st.session_state.leaderboard = msg.get('leaderboard', [])
        st.session_state.status_message = msg.get('message', 'Game Over!')
        st.session_state.force_refresh = True
    
    elif msg_type == 'player_joined':
        st.toast(f"🎮 {msg.get('name')} joined!")
    
    elif msg_type == 'player_left':
        st.toast(f"👋 {msg.get('name')} left")
    
    elif msg_type == 'disconnected':
        st.session_state.status_message = "Disconnected from server"
        disconnect_from_server()
        st.session_state.force_refresh = True
    
    elif msg_type == 'error':
        st.session_state.status_message = msg.get('message', 'Error occurred')
        st.session_state.force_refresh = True


def submit_answer(answer_index):
    """Submit answer to server."""
    if st.session_state.answered or not st.session_state.socket:
        return
    
    send_json(st.session_state.socket, {
        "type": "answer",
        "answer": answer_index
    })
    st.session_state.answered = True


def start_game():
    """Request server to start the game (admin function)."""
    if st.session_state.socket:
        send_json(st.session_state.socket, {"type": "start_game"})


# Main UI
st.markdown('<h1 class="main-header">🎮 TCP Kahoot Quiz</h1>', unsafe_allow_html=True)

# Process incoming messages only if connected
if st.session_state.connected:
    # Check for new messages
    has_messages = not st.session_state.message_queue.empty()
    
    if has_messages:
        # Process all pending messages
        while not st.session_state.message_queue.empty():
            try:
                msg = st.session_state.message_queue.get_nowait()
                handle_server_message(msg)
            except queue.Empty:
                break
        # Force rerun after processing messages
        time.sleep(0.05)
        rerun()
    
    # Auto-refresh for timer countdown
    if st.session_state.game_state == "playing" and not st.session_state.answered:
        current_time = time.time()
        if current_time - st.session_state.last_update >= 1.0:
            st.session_state.last_update = current_time
            if st.session_state.time_left > 0:
                st.session_state.time_left -= 1
            time.sleep(0.05)
            rerun()

# Connection Section
if not st.session_state.connected:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔌 Connect to Server")
        
        host = st.text_input("Server IP", value="localhost", key="host_input")
        port = st.number_input("Port", value=8888, min_value=1, max_value=65535, key="port_input")
        player_name = st.text_input("Your Name", placeholder="Enter your name", key="name_input")
        
        if st.button("Connect", type="primary", use_container_width=True):
            if not player_name.strip():
                st.error("Please enter your name!")
            else:
                with st.spinner("Connecting to server..."):
                    success, message = connect_to_server(host, port, player_name)
                    
                    if success:
                        st.success(message)
                        time.sleep(1)
                        rerun()
                    else:
                        st.error(message)
        
        # Instructions
        with st.expander("📖 Instructions"):
            st.markdown("""
            ### How to Play:
            1. **Start the Server** first (in another terminal)
            2. **Enter server details** and your name
            3. **Connect** and wait for other players
            4. **Click 'Start Game'** when ready (any player can start)
            5. **Answer questions** as fast as you can for bonus points!
            6. **First correct answer** gets +100 bonus points
            
            ### Scoring:
            - Base points: 100 per correct answer
            - Speed bonus: Up to 50 points (faster = more points)
            - First correct: +100 bonus points
            """)

# Game Interface
else:
    # Header with player info
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.metric("👤 Player", st.session_state.player_name)
    
    with col2:
        if st.session_state.game_state == "playing":
            st.metric("❓ Question", f"{st.session_state.question_number}/{st.session_state.total_questions}")
    
    with col3:
        st.metric("🏆 Score", st.session_state.score)
    
    # Disconnect button
    if st.button("🚪 Disconnect", type="secondary"):
        disconnect_from_server()
        rerun()
    
    st.markdown("---")
    
    # DEBUG: Show current state
    with st.expander("🔍 Debug: Current State"):
        st.write(f"**Game State:** {st.session_state.game_state}")
        st.write(f"**Connected:** {st.session_state.connected}")
        st.write(f"**Current Question:** {st.session_state.current_question}")
        st.write(f"**Question Number:** {st.session_state.question_number}/{st.session_state.total_questions}")
        st.write(f"**Answered:** {st.session_state.answered}")
        st.write(f"**Time Left:** {st.session_state.time_left}")
    
    # Status message
    if st.session_state.status_message:
        st.info(st.session_state.status_message)
    
    # Waiting State
    if st.session_state.game_state == "waiting":
        st.markdown("### ⏳ Waiting for game to start...")
        
        st.info("💡 Any player can start the game using the button below")
        
        # Admin controls
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🎮 Start Game", type="primary", use_container_width=True):
                start_game()
                st.success("Game start request sent!")
                time.sleep(1)
                rerun()
    
    # Playing State
    elif st.session_state.game_state == "playing" and st.session_state.current_question:
        question = st.session_state.current_question
        
        # Debug info
        st.sidebar.write("**Debug Info:**")
        st.sidebar.write(f"Game State: {st.session_state.game_state}")
        st.sidebar.write(f"Question #{st.session_state.question_number}")
        st.sidebar.write(f"Has Question: {st.session_state.current_question is not None}")
        st.sidebar.write(f"Answered: {st.session_state.answered}")
        
        # Progress bar
        progress = st.session_state.question_number / st.session_state.total_questions if st.session_state.total_questions > 0 else 0
        st.progress(progress, text=f"Progress: {st.session_state.question_number}/{st.session_state.total_questions}")
        
        # Timer
        timer_col1, timer_col2, timer_col3 = st.columns([1, 2, 1])
        with timer_col2:
            time_color = "#ff4444" if st.session_state.time_left <= 5 else "#4CAF50"
            st.markdown(f"<h2 style='text-align: center; color: {time_color};'>⏱️ {st.session_state.time_left}s</h2>", 
                       unsafe_allow_html=True)
        
        # Question
        st.markdown(f'<div class="question-box">{question["question"]}</div>', unsafe_allow_html=True)
        
        # Answer result feedback
        if st.session_state.answer_result:
            result = st.session_state.answer_result
            if result['correct']:
                st.success(f"✅ {result['message']}")
            else:
                st.error(f"❌ {result['message']}")
        
        # Answer buttons
        st.markdown("### Choose your answer:")
        
        col1, col2 = st.columns(2)
        
        colors = ["🔴", "🔵", "🟡", "🟢"]
        
        for idx, option in enumerate(question['options']):
            target_col = col1 if idx % 2 == 0 else col2
            
            with target_col:
                button_label = f"{colors[idx]} {option}"
                
                if st.button(
                    button_label,
                    key=f"answer_{idx}",
                    disabled=st.session_state.answered,
                    use_container_width=True,
                    type="secondary"
                ):
                    submit_answer(idx)
                    rerun()
        
        # Leaderboard in sidebar
        if st.session_state.leaderboard:
            with st.sidebar:
                st.subheader("🏆 Current Leaderboard")
                for i, player in enumerate(st.session_state.leaderboard[:10], 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    highlight = "**" if player['name'] == st.session_state.player_name else ""
                    st.write(f"{highlight}{medal} {player['name']} - {player['score']} pts{highlight}")
    
    # Results State
    elif st.session_state.game_state == "results":
        st.balloons()
        
        st.markdown("## 🎉 Game Over! Final Results")
        
        if st.session_state.leaderboard:
            # Top 3 podium
            if len(st.session_state.leaderboard) >= 3:
                col1, col2, col3 = st.columns(3)
                
                with col2:  # 1st place center
                    st.markdown("### 🥇 First Place")
                    st.markdown(f"### {st.session_state.leaderboard[0]['name']}")
                    st.markdown(f"## {st.session_state.leaderboard[0]['score']} pts")
                
                with col1:  # 2nd place left
                    if len(st.session_state.leaderboard) >= 2:
                        st.markdown("### 🥈 Second Place")
                        st.markdown(f"### {st.session_state.leaderboard[1]['name']}")
                        st.markdown(f"## {st.session_state.leaderboard[1]['score']} pts")
                
                with col3:  # 3rd place right
                    if len(st.session_state.leaderboard) >= 3:
                        st.markdown("### 🥉 Third Place")
                        st.markdown(f"### {st.session_state.leaderboard[2]['name']}")
                        st.markdown(f"## {st.session_state.leaderboard[2]['score']} pts")
            
            st.markdown("---")
            
            # Full leaderboard
            st.subheader("📊 Complete Rankings")
            for i, player in enumerate(st.session_state.leaderboard, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                
                # Highlight current player
                if player['name'] == st.session_state.player_name:
                    st.markdown(f"**{medal} {player['name']} - {player['score']} points** ⭐")
                else:
                    st.write(f"{medal} {player['name']} - {player['score']} points")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Play Again", type="primary", use_container_width=True):
                st.session_state.score = 0
                st.session_state.game_state = "waiting"
                st.session_state.status_message = "Waiting for next game..."
                rerun()
        
        with col2:
            if st.button("🚪 Exit", type="secondary", use_container_width=True):
                disconnect_from_server()
                rerun()


# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <strong>CS411 Computer Networks Project</strong><br>
    Mediterranean Institute of Technology (SMU)<br>
    Instructor: M. Iheb Hergli
</div>
""", unsafe_allow_html=True)

# Auto-refresh mechanism
if st.session_state.connected:
    # Check if we need to refresh
    if st.session_state.force_refresh or not st.session_state.message_queue.empty():
        st.session_state.force_refresh = False
        time.sleep(0.1)
        rerun()
    
    # Periodic refresh when playing
    if st.session_state.game_state == "playing":
        time.sleep(0.5)
        rerun()