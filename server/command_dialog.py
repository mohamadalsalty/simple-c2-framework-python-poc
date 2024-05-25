import socket
import threading
import traceback
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QTextEdit, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal

class CommandDialog(QDialog):
    append_output_signal = pyqtSignal(str, str)

    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.initUI()
        self.append_output_signal.connect(self.appendOutput)

    def initUI(self):
        self.setWindowTitle(f"Command Execution for {self.agent.name}")
        self.setGeometry(100, 100, 600, 400)

        self.layout = QVBoxLayout(self)

        self.command_input = QLineEdit(self)
        self.command_input.setPlaceholderText("Enter command")
        self.layout.addWidget(self.command_input)

        self.output_text = QTextEdit(self)
        self.output_text.setReadOnly(True)
        self.layout.addWidget(self.output_text)

        self.execute_button = QPushButton("Execute", self)
        self.execute_button.clicked.connect(self.executeCommand)
        self.layout.addWidget(self.execute_button)

    def executeCommand(self):
        command = self.command_input.text().strip()
        if command:
            try:
                temp_port = self.startTempServer(command)
                self.agent.socket.sendall(f"COMMAND_PORT {temp_port}".encode('utf-8'))
                self.command_input.clear()
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
            client_socket.sendall(command.encode('utf-8'))
            response = client_socket.recv(1024).decode('utf-8')
            self.append_output_signal.emit(command, response)
            client_socket.close()
        except Exception as e:
            self.append_output_signal.emit(command, f"Error executing command: {e}")
            traceback.print_exc()
        finally:
            temp_socket.close()

    def appendOutput(self, command, response):
        self.output_text.append(f"> {command}\n{response}\n")

