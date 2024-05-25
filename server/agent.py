import time

class Agent:
    def __init__(self, name, ip, user, socket):
        self.name = name
        self.ip = ip
        self.user = user
        self.socket = socket
        self.last_seen = time.time()
        self.alive = True
