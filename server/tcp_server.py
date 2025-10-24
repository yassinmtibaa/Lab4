"""
TCP Kahoot Server - CS411 Computer Networks Project
Handles multiple clients concurrently with thread-safe state management.
"""

import socket
import threading
import json
import time
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.utils import send_json, recv_json, close_socket_safe


class KahootServer:
    def __init__(self, host='0.0.0.0', port=8888, questions_file='questions/sample_questions.json'):
        """
        Initialize the Kahoot TCP server.
        
        Args:
            host: IP address to bind to (0.0.0.0 = all interfaces)
            port: TCP port to listen on
            questions_file: Path to JSON file with quiz questions
        """
        self.host = host
        self.port = port
        self.questions_file = questions_file
        
        # Thread-safe shared state
        self.clients = {}  # {socket: {"name": str, "score": int, "answered": bool}}
        self.lock = threading.Lock()
        
        # Game state
        self.questions = []
        self.current_question_idx = -1
        self.game_started = False
        self.question_start_time = None
        self.first_correct_awarded = False
        
        # Server socket
        self.server_socket = None
        self.running = False
        
        # Load questions
        self.load_questions()
    
    def load_questions(self):
        """Load quiz questions from JSON file."""
        try:
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.questions = data.get('questions', [])
                print(f"[INFO] Loaded {len(self.questions)} questions")
        except FileNotFoundError:
            print(f"[ERROR] Questions file not found: {self.questions_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in questions file: {e}")
            sys.exit(1)
    
    def start(self):
        """Start the TCP server and listen for connections."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"[INFO] Server started on {self.host}:{self.port}")
            print(f"[INFO] Waiting for clients...")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"[INFO] New connection from {client_address}")
                    
                    # Start client handler thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"[ERROR] Accept error: {e}")
        
        except Exception as e:
            print(f"[ERROR] Server startup failed: {e}")
        finally:
            self.shutdown()
    
    def handle_client(self, client_socket, client_address):
        """
        Handle individual client connection in separate thread.
        
        Args:
            client_socket: Connected client socket
            client_address: Client's address tuple (ip, port)
        """
        player_name = None
        
        try:
            # Wait for player registration
            msg = recv_json(client_socket)
            if not msg or msg.get('type') != 'register':
                send_json(client_socket, {"type": "error", "message": "Invalid registration"})
                return
            
            player_name = msg.get('name', 'Anonymous')
            
            # Register client
            with self.lock:
                self.clients[client_socket] = {
                    "name": player_name,
                    "score": 0,
                    "answered": False,
                    "address": client_address
                }
            
            print(f"[INFO] Player '{player_name}' registered from {client_address}")
            
            # Send registration confirmation
            send_json(client_socket, {
                "type": "registered",
                "name": player_name,
                "message": "Successfully registered!"
            })
            
            # Broadcast player join
            self.broadcast({
                "type": "player_joined",
                "name": player_name,
                "total_players": len(self.clients)
            })
            
            # Send current game state
            if self.game_started:
                self.send_current_question(client_socket)
            else:
                send_json(client_socket, {
                    "type": "waiting",
                    "message": "Waiting for game to start..."
                })
            
            # Handle client messages
            while self.running:
                msg = recv_json(client_socket)
                
                if not msg:
                    break  # Client disconnected
                
                msg_type = msg.get('type')
                
                if msg_type == 'answer':
                    self.handle_answer(client_socket, msg)
                
                elif msg_type == 'start_game' and len(self.clients) > 0:
                    self.start_game()
                
                elif msg_type == 'next_question':
                    self.next_question()
        
        except Exception as e:
            print(f"[ERROR] Client handler error for {player_name}: {e}")
        
        finally:
            # Clean up client
            with self.lock:
                if client_socket in self.clients:
                    player_name = self.clients[client_socket]["name"]
                    del self.clients[client_socket]
            
            close_socket_safe(client_socket)
            
            if player_name:
                print(f"[INFO] Player '{player_name}' disconnected")
                self.broadcast({
                    "type": "player_left",
                    "name": player_name,
                    "total_players": len(self.clients)
                })
    
    def handle_answer(self, client_socket, msg):
        """
        Process answer submission from client.
        Awards bonus points to first correct answer.
        """
        with self.lock:
            # Check if client already answered
            if self.clients[client_socket]["answered"]:
                send_json(client_socket, {
                    "type": "error",
                    "message": "You already answered this question"
                })
                return
            
            # Mark as answered
            self.clients[client_socket]["answered"] = True
            
            answer = msg.get('answer')
            player_name = self.clients[client_socket]["name"]
            
            # Get current question
            if self.current_question_idx < 0 or self.current_question_idx >= len(self.questions):
                return
            
            question = self.questions[self.current_question_idx]
            correct_answer = question['correct_answer']
            base_points = question['points']
            
            # Check if answer is correct
            is_correct = (answer == correct_answer)
            
            if is_correct:
                # Calculate time bonus (faster = more points)
                elapsed = time.time() - self.question_start_time if self.question_start_time else 20
                time_bonus = max(0, int((20 - elapsed) / 20 * 50))  # Up to 50 bonus points
                
                points = base_points + time_bonus
                
                # Award bonus for first correct answer
                if not self.first_correct_awarded:
                    points += 100
                    self.first_correct_awarded = True
                    bonus_msg = " (First correct +100!)"
                else:
                    bonus_msg = ""
                
                self.clients[client_socket]["score"] += points
                
                print(f"[INFO] {player_name} answered correctly! +{points} points{bonus_msg}")
                
                # Send feedback to player
                send_json(client_socket, {
                    "type": "answer_result",
                    "correct": True,
                    "points": points,
                    "message": f"Correct! +{points} points{bonus_msg}"
                })
            else:
                print(f"[INFO] {player_name} answered incorrectly")
                send_json(client_socket, {
                    "type": "answer_result",
                    "correct": False,
                    "points": 0,
                    "message": "Incorrect answer"
                })
            
            # Check if all players answered
            all_answered = all(client["answered"] for client in self.clients.values())
            if all_answered:
                # Send reveal and leaderboard after short delay
                threading.Timer(2.0, self.reveal_answer).start()
    
    def start_game(self):
        """Start the quiz game and send first question."""
        with self.lock:
            if self.game_started:
                return
            
            self.game_started = True
            self.current_question_idx = -1
            
            # Reset all scores
            for client in self.clients.values():
                client["score"] = 0
                client["answered"] = False
        
        print("[INFO] Game started!")
        self.broadcast({
            "type": "game_started",
            "total_questions": len(self.questions)
        })
        
        # Send first question after 2 seconds
        threading.Timer(2.0, self.next_question).start()
    
    def next_question(self):
        """Advance to next question and broadcast to all clients."""
        with self.lock:
            self.current_question_idx += 1
            
            # Check if game over
            if self.current_question_idx >= len(self.questions):
                self.end_game()
                return
            
            # Reset answered flags
            for client in self.clients.values():
                client["answered"] = False
            
            self.first_correct_awarded = False
            self.question_start_time = time.time()
        
        # Send question to all clients
        question = self.questions[self.current_question_idx]
        print(f"[INFO] Sending question {self.current_question_idx + 1}/{len(self.questions)}")
        print(f"[DEBUG] Question text: {question['question']}")
        print(f"[DEBUG] Connected clients: {len(self.clients)}")
        
        question_msg = {
            "type": "question",
            "question_number": self.current_question_idx + 1,
            "total_questions": len(self.questions),
            "question": question['question'],
            "options": question['options'],
            "time_limit": 20
        }
        
        print(f"[DEBUG] Broadcasting message: {question_msg}")
        self.broadcast(question_msg)
    
    def send_current_question(self, client_socket):
        """Send current question to a specific client (for late joiners)."""
        if self.current_question_idx >= 0 and self.current_question_idx < len(self.questions):
            question = self.questions[self.current_question_idx]
            send_json(client_socket, {
                "type": "question",
                "question_number": self.current_question_idx + 1,
                "total_questions": len(self.questions),
                "question": question['question'],
                "options": question['options'],
                "time_limit": 20
            })
    
    def reveal_answer(self):
        """Reveal correct answer and send leaderboard."""
        if self.current_question_idx < 0 or self.current_question_idx >= len(self.questions):
            return
        
        question = self.questions[self.current_question_idx]
        correct_answer = question['correct_answer']
        
        self.broadcast({
            "type": "answer_reveal",
            "correct_answer": correct_answer,
            "explanation": f"The correct answer was: {question['options'][correct_answer]}"
        })
        
        # Send leaderboard
        self.send_leaderboard()
        
        # Auto-advance to next question after 3 seconds
        threading.Timer(3.0, self.next_question).start()
    
    def send_leaderboard(self):
        """Send current leaderboard to all clients."""
        with self.lock:
            leaderboard = [
                {"name": client["name"], "score": client["score"]}
                for client in self.clients.values()
            ]
            leaderboard.sort(key=lambda x: x["score"], reverse=True)
        
        self.broadcast({
            "type": "leaderboard",
            "leaderboard": leaderboard
        })
    
    def end_game(self):
        """End the game and send final results."""
        print("[INFO] Game ended!")
        
        with self.lock:
            leaderboard = [
                {"name": client["name"], "score": client["score"]}
                for client in self.clients.values()
            ]
            leaderboard.sort(key=lambda x: x["score"], reverse=True)
        
        self.broadcast({
            "type": "game_over",
            "leaderboard": leaderboard,
            "message": "Game Over! Thanks for playing!"
        })
        
        # Reset game state
        with self.lock:
            self.game_started = False
            self.current_question_idx = -1
    
    def broadcast(self, message):
        """
        Send message to all connected clients.
        
        Args:
            message: Dictionary to send as JSON
        """
        with self.lock:
            dead_sockets = []
            
            for client_socket in list(self.clients.keys()):
                if not send_json(client_socket, message):
                    dead_sockets.append(client_socket)
            
            # Remove dead connections
            for sock in dead_sockets:
                if sock in self.clients:
                    del self.clients[sock]
                close_socket_safe(sock)
    
    def shutdown(self):
        """Gracefully shutdown the server."""
        print("[INFO] Shutting down server...")
        self.running = False
        
        # Close all client connections
        with self.lock:
            for client_socket in list(self.clients.keys()):
                close_socket_safe(client_socket)
            self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            close_socket_safe(self.server_socket)
        
        print("[INFO] Server stopped")


def main():
    """Main entry point."""
    print("=" * 50)
    print("   TCP Kahoot Server - CS411 Project")
    print("   Mediterranean Institute of Technology")
    print("=" * 50)
    
    server = KahootServer(host='0.0.0.0', port=8888)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INFO] Server interrupted by user")
        server.shutdown()


if __name__ == "__main__":
    main()