import socket
import json

# Connect to server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 8888))

# Register
msg = json.dumps({"type": "register", "name": "test"}) + '\n'
sock.sendall(msg.encode('utf-8'))

# Read all messages
while True:
    data = sock.recv(4096).decode('utf-8')
    print(f"RECEIVED: {data}")
    if not data:
        break