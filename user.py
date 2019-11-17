#declare imports
from Queue import Queue
import util

"""
This class helps to differentiate between users on different threads 
Note that due to the multi-threading application Queue has been used to ensure 'thread-safe' data structures
"""
class User:
    def __init__(self, username, password):
        self.username = username #username ---> Credentials.txt first column
        self.password = password #password ---> Credential.txt second column
        self.is_connected = False#boolean indicative of user being 'logged_in' state or 'logged_out'state
        self.last_active = float('-inf') #keeps track of when the user was last active (used for the implemntation of timeout)
        self.blocked_connections = {}    #keeps track of connections blocked when dealing with authentication
        self.blocked_users = []          #keeps track of users blocked(used for the implementation of block and unblock commands)
        self.message_queue = Queue()     #keeps track of the messeges yet to be viewed by the user 

    def login(self):
        self.is_connected = True
        #login is the first user active command
        self.register_activity()

    #resets the .last_active variable everytime the user is active 
    #called by the server 
    def register_activity(self):
        self.last_active = util.current_time()

    def logout(self):
        self.is_connected = False

    #add messeges to the messege_queue
    def add_messeges(self, message):
        self.message_queue.put(message)

    #goes through the messege_queue and temporarily stores each of the messeges in the messeges list 
    #returns the messenges list
    def dump_message_queue(self):
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages

"""
This class helps to keep the data relevant to Messeges in one class
"""
class Message:
    def __init__(self, message_string, from_user):
        self.message_string = message_string #messege body from user
        self.from_user = from_user #messege sender details
        self.timestamp = util.current_time_string() #time messege was first sent

    def __str__(self):
        return '[{}] {}: {}'.format(
            self.timestamp,
            self.from_user.username,
            self.message_string
        )

