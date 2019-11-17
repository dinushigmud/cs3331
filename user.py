from Queue import Queue
import util

class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.is_connected = False
        self.last_active = float('-inf')
        self.blocked_ips = {}
        self.message_queue = Queue()  # thread-safe

    def login(self):
        self.is_connected = True
        self.register_activity()

    def register_activity(self):
        self.last_active = util.current_time()

    def logout(self):
        self.is_connected = False

    def enqueue_message(self, message):
        self.message_queue.put(message)

    def dump_message_queue(self):
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages


class Message:
    def __init__(self, message_string, from_user):
        self.message_string = message_string
        self.from_user = from_user
        self.timestamp = util.current_time_string()

    def __str__(self):
        return '[{}] {}: {}'.format(
            self.timestamp,
            self.from_user.username,
            self.message_string
        )

