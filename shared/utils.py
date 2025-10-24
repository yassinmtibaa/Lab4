"""
Shared utility functions for TCP JSON communication.
Implements newline-delimited JSON (LD-JSON) for message framing.
"""

import json
import socket
from typing import Any, Optional


def send_json(sock: socket.socket, obj: Any) -> bool:
    """
    Send a JSON object over TCP with newline delimiter.
    
    Args:
        sock: The socket to send data through
        obj: Python object to serialize (dict, list, etc.)
    
    Returns:
        bool: True if successful, False otherwise
    
    Protocol:
        Each message is JSON followed by '\n' for framing.
        Example: {"type":"question","data":"..."}\n
    """
    try:
        # Serialize to JSON and add newline delimiter
        message = json.dumps(obj) + '\n'
        # Encode to bytes (UTF-8)
        sock.sendall(message.encode('utf-8'))
        return True
    except (socket.error, json.JSONDecodeError, TypeError) as e:
        print(f"[ERROR] send_json failed: {e}")
        return False


def recv_json(sock: socket.socket, buffer_size: int = 4096) -> Optional[Any]:
    """
    Receive a newline-delimited JSON message from TCP socket.
    
    Args:
        sock: The socket to receive data from
        buffer_size: Maximum bytes to read per recv() call
    
    Returns:
        Parsed Python object, or None on error/disconnect
    
    Protocol:
        Reads until '\n' delimiter is found, then parses JSON.
        Handles partial reads and buffering automatically.
    
    Thread Safety:
        This function is NOT thread-safe if multiple threads
        call recv_json on the same socket simultaneously.
        Use one reader thread per socket.
    """
    buffer = ""
    
    try:
        while True:
            # Receive chunk of data
            chunk = sock.recv(buffer_size)
            
            # Empty recv means socket closed
            if not chunk:
                print("[INFO] Socket closed by peer")
                return None
            
            # Decode chunk
            try:
                decoded = chunk.decode('utf-8')
            except UnicodeDecodeError as e:
                print(f"[ERROR] Unicode decode error: {e}")
                continue
            
            buffer += decoded
            
            # Check for newline delimiter
            if '\n' in buffer:
                # Extract first complete message
                message, remaining = buffer.split('\n', 1)
                
                # Parse JSON
                try:
                    obj = json.loads(message)
                    return obj
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Invalid JSON: {message[:100]}")
                    print(f"[ERROR] JSON error: {e}")
                    # Try to continue with remaining buffer
                    buffer = remaining
                    continue
                
    except socket.timeout:
        # Timeout is normal for non-blocking operations
        return None
    except socket.error as e:
        print(f"[ERROR] Socket error in recv_json: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error in recv_json: {e}")
        import traceback
        traceback.print_exc()
        return None


def set_socket_timeout(sock: socket.socket, timeout: Optional[float] = None):
    """
    Configure socket timeout for recv operations.
    
    Args:
        sock: Socket to configure
        timeout: Timeout in seconds (None = blocking)
    """
    sock.settimeout(timeout)


def close_socket_safe(sock: socket.socket):
    """
    Safely close a socket with error handling.
    
    Args:
        sock: Socket to close
    """
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass  # Socket may already be closed
    
    try:
        sock.close()
    except:
        pass