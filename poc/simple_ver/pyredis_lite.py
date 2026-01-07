
import socket
import threading
import time
from collections import defaultdict

class PyRedisLite:
    def __init__(self):
        self.data = {}
        self.expirations = {}
        self.lock = threading.Lock()

    def set(self, key, value, ex=None):
        with self.lock:
            self.data[key] = value
            if ex:
                self.expirations[key] = time.time() + int(ex)
            return "OK"

    def get(self, key):
        with self.lock:
            if key in self.data:
                if key in self.expirations and time.time() > self.expirations[key]:
                    del self.data[key]
                    del self.expirations[key]
                    return "(nil)"
                return self.data[key]
            return "(nil)"

    def delete(self, key):
        with self.lock:
            if key in self.data:
                del self.data[key]
                if key in self.expirations:
                    del self.expirations[key]
                return "1"
            return "0"

    def exists(self, key):
        with self.lock:
            if key in self.data:
                if key in self.expirations and time.time() > self.expirations[key]:
                    del self.data[key]
                    del self.expirations[key]
                    return "0"
                return "1"
            return "0"

    def ttl(self, key):
        with self.lock:
            if key in self.data:
                if key in self.expirations:
                    if time.time() > self.expirations[key]:
                        del self.data[key]
                        del self.expirations[key]
                        return "-2"
                    return str(int(self.expirations[key] - time.time()))
                return "-1"
            return "-2"

    def incr(self, key):
        with self.lock:
            if key in self.data:
                try:
                    self.data[key] = str(int(self.data[key]) + 1)
                    return self.data[key]
                except ValueError:
                    return "ERROR: Value is not an integer"
            else:
                self.data[key] = "1"
                return "1"

    def flushall(self):
        with self.lock:
            self.data.clear()
            self.expirations.clear()
            return "OK"

    def active_expire(self):
        while True:
            with self.lock:
                keys_to_delete = []
                for key, expiration_time in self.expirations.items():
                    if time.time() > expiration_time:
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    if key in self.data:
                        del self.data[key]
                    del self.expirations[key]
            time.sleep(1)

def handle_client(client_socket, db):
    while True:
        try:
            command = client_socket.recv(1024).decode().strip()
            if not command:
                break
            parts = command.split()
            cmd = parts[0].upper()
            args = parts[1:]

            if cmd == "SET" and len(args) == 2:
                response = db.set(args[0], args[1])
            elif cmd == "SET" and len(args) == 4 and args[2].upper() == "EX":
                response = db.set(args[0], args[1], ex=args[3])
            elif cmd == "GET" and len(args) == 1:
                response = db.get(args[0])
            elif cmd == "DEL" and len(args) == 1:
                response = db.delete(args[0])
            elif cmd == "EXISTS" and len(args) == 1:
                response = db.exists(args[0])
            elif cmd == "TTL" and len(args) == 1:
                response = db.ttl(args[0])
            elif cmd == "INCR" and len(args) == 1:
                response = db.incr(args[0])
            elif cmd == "FLUSHALL" and len(args) == 0:
                response = db.flushall()
            else:
                response = "ERROR: Unknown command or wrong number of arguments"
            
            client_socket.sendall((response + "\n").encode())
        except ConnectionResetError:
            break
        except Exception as e:
            client_socket.sendall((f"ERROR: {e}\n").encode())
            break
    client_socket.close()

def main():
    db = PyRedisLite()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 6379))
    server.listen(5)
    print("PyRedisLite server started on port 6379")

    active_expire_thread = threading.Thread(target=db.active_expire)
    active_expire_thread.daemon = True
    active_expire_thread.start()

    while True:
        client_sock, addr = server.accept()
        print(f"Accepted connection from {addr[0]}:{addr[1]}")
        client_handler = threading.Thread(target=handle_client, args=(client_sock, db))
        client_handler.start()

if __name__ == "__main__":
    main()
