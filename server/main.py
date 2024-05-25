import sys
import socket
import threading
import time
import traceback
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QMessageBox, QMenu, QInputDialog
from PyQt5.QtCore import Qt, QTimer, QSize
from .agent import Agent
from .communication import Communicate
from .command_dialog import CommandDialog

class AgentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.comm = Communicate()
        self.comm.new_agent_signal.connect(self.addAgentToList)
        self.comm.command_response_signal.connect(self.showCommandResponse)
        self.comm.update_agent_status_signal.connect(self.updateAgentStatus)
        self.agents = []
        self.startServer()
        self.startAliveCheck()

    def initUI(self):
        layout = QVBoxLayout()

        self.agent_list_widget = QListWidget()
        self.agent_list_widget.setStyleSheet("""
            QListWidget {
                background-color: black;
                color: white;
                font-size: 18px;
                padding: 10px;
            }
            QListWidget::item {
                height: 50px;
                border: 1px solid white;
                padding: 10px;
                margin: 5px;
            }
        """)

        self.agent_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.agent_list_widget.customContextMenuRequested.connect(self.showContextMenu)

        layout.addWidget(self.agent_list_widget)
        self.setLayout(layout)
        self.setWindowTitle('Agent List')
        self.resize(800, 600)  # Increase the window size for a larger view
        self.show()

    def addAgentToList(self, agent):
        self.agents.append(agent)
        item = QListWidgetItem(f"{agent.name} ({agent.ip})")
        item.setData(Qt.UserRole, agent)
        item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.agent_list_widget.addItem(item)

    def updateAgentStatus(self):
        current_time = time.time()
        for i in range(self.agent_list_widget.count()):
            item = self.agent_list_widget.item(i)
            agent = item.data(Qt.UserRole)
            if current_time - agent.last_seen > 5:  # 5 seconds timeout for dead status
                agent.alive = False
                item.setBackground(Qt.red)
            else:
                agent.alive = True
                item.setBackground(Qt.green)

    def showContextMenu(self, pos):
        item = self.agent_list_widget.itemAt(pos)
        if item:
            agent = item.data(Qt.UserRole)
            menu = QMenu(self)
            name_action = menu.addAction(f"Name: {agent.name}")
            ip_action = menu.addAction(f"IP: {agent.ip}")
            exec_command_action = menu.addAction("Execute Command")
            delete_action = menu.addAction("Delete Agent")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == name_action:
                QMessageBox.information(self, "Agent Details", f"Name: {agent.name}")
            elif action == ip_action:
                self.showIPConfig(agent.ip)
            elif action == exec_command_action:
                self.openCommandDialog(agent)
            elif action == delete_action:
                self.deleteAgent(agent)

    def openCommandDialog(self, agent):
        self.command_dialog = CommandDialog(agent, self)
        self.command_dialog.show()

    def showIPConfig(self, ip):
        QMessageBox.information(self, "IP Address", f"IP Address: {ip}")

    def deleteAgent(self, agent):
        try:
            if agent.alive:
                self.sendCommand(agent, 'EXIT')  # Send EXIT command to the agent
                time.sleep(1)  # Give some time for the client to exit
            self.agents.remove(agent)
            for i in range(self.agent_list_widget.count()):
                item = self.agent_list_widget.item(i)
                if item.data(Qt.UserRole) == agent:
                    self.agent_list_widget.takeItem(i)
                    break
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete agent: {str(e)}")
            traceback.print_exc()

    def sendCommand(self, agent, command):
        try:
            temp_port = self.startTempServer(command)
            agent.socket.sendall(f"COMMAND_PORT {temp_port}".encode('utf-8'))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send command: {str(e)}")
            traceback.print_exc()

    def startTempServer(self, command):
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_socket.bind(('0.0.0.0', 0))
        temp_socket.listen(1)
        port = temp_socket.getsockname()[1]

        threading.Thread(target=self.handleTempConnection, args=(temp_socket, command)).start()
        return port

    def handleTempConnection(self, temp_socket, command):
        try:
            client_socket, addr = temp_socket.accept()
            print(f"Temporary connection from {addr} for command execution")
            client_socket.sendall(command.encode('utf-8'))
            response = client_socket.recv(1024).decode('utf-8')
            print(f"Command response: {response}")
            self.comm.command_response_signal.emit(command, response)
            client_socket.close()
        except Exception as e:
            print(f"Error in temporary connection: {e}")
            traceback.print_exc()
        finally:
            temp_socket.close()

    def startServer(self):
        while True:
            port, ok = QInputDialog.getInt(self, "Select Port", "Enter port number to listen on:")
            if not ok:
                sys.exit()
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.bind(('0.0.0.0', port))
                self.server_socket.listen(5)
                print(f"Server started on port {port}, waiting for connections...")
                self.server_thread = threading.Thread(target=self.serverLoop)
                self.server_thread.daemon = True
                self.server_thread.start()
                break
            except OSError:
                QMessageBox.critical(self, "Error", f"Port {port} is already in use. Please try another port.")
                self.server_socket.close()

    def serverLoop(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Connection from {addr}")
            threading.Thread(target=self.handleClient, args=(client_socket, addr)).start()

    def handleClient(self, client_socket, addr):
        try:
            with client_socket:
                agent_info = client_socket.recv(1024).decode('utf-8')
                name, ip_address = agent_info.split(',')
                print(f"Connected to {name} with IP {ip_address}")

                new_agent = Agent(name, ip_address, None, client_socket)
                self.comm.new_agent_signal.emit(new_agent)
                
                while True:
                    try:
                        data = client_socket.recv(1024)
                        if not data:
                            break
                        print(f"Received from {name}: {data.decode('utf-8')}")
                        new_agent.last_seen = time.time()
                    except ConnectionResetError:
                        break
        except Exception as e:
            print(f"Error handling client {addr}: {str(e)}")
            traceback.print_exc()
        finally:
            print(f"Connection closed for {name}")

    def startAliveCheck(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_alive)
        self.timer.start(2000)  # check every 2 seconds

    def check_alive(self):
        for agent in self.agents:
            if agent.alive:
                try:
                    temp_port = self.startPingServer(agent)
                    agent.socket.sendall(f"PING_PORT {temp_port}".encode('utf-8'))
                except Exception as e:
                    print(f"Error sending ping: {e}")
                    traceback.print_exc()
                    agent.alive = False
        self.comm.update_agent_status_signal.emit()

    def startPingServer(self, agent):
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_socket.bind(('0.0.0.0', 0))
        temp_socket.listen(1)
        port = temp_socket.getsockname()[1]

        threading.Thread(target=self.handlePingConnection, args=(temp_socket, agent)).start()
        return port

    def handlePingConnection(self, temp_socket, agent):
        try:
            client_socket, addr = temp_socket.accept()
            print(f"Ping connection from {addr}")
            client_socket.recv(1024)  # Read the PONG message
            agent.last_seen = time.time()
            client_socket.close()
        except Exception as e:
            print(f"Error in ping connection: {e}")
            traceback.print_exc()
        finally:
            temp_socket.close()

    def showCommandResponse(self, command, response):
        QMessageBox.information(self, "Command Response", f"Command: {command}\nResponse: {response}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AgentApp()
    sys.exit(app.exec_())
