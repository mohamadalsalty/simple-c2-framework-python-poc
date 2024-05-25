from PyQt5.QtCore import QObject, pyqtSignal

class Communicate(QObject):
    new_agent_signal = pyqtSignal(object)
    command_response_signal = pyqtSignal(str, str)
    update_agent_status_signal = pyqtSignal()

