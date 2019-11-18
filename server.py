
import os
import socket
import SocketServer
import sys
import user
import re
import time 
from Queue import Queue

BUFFER_SIZE = 1024

#basically breaks down the arguments into the main 'command' and then the rest of the 'args'
#helper function to process_commands function in server.py
def parse_command(command_string):
    tokens = command_string.split()
    if not tokens:
        return None, []
    command, args = tokens[0], tokens[1:]
    for i in range(len(args)):
        if i == 0 and args[i][0] == '(' and args[i][-1] == ')':
            args[i] = re.split('\s+', args[i][1:-1])
        elif args[i][0] == '\'' and args[i][-1] == '\'':
            args[i] = args[i][1:-1]
    return command, args


#returns current time
def current_time():
    return int(time.time())

#returns the current time in string format 
def current_time_string():
    return time.strftime('%m-%d-%yT%H:%M:%S')

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
        self.last_active = current_time()

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
        self.timestamp = current_time_string() #time messege was first sent

    def __str__(self):
        return '[{}] {}: {}'.format(
            self.timestamp,
            self.from_user.username,
            self.message_string
        )

class Server(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, request_handler_class, user_file_path):
        SocketServer.TCPServer.__init__(self, server_address,request_handler_class)
        self.load_users(user_file_path)
        self.daemon_threads = True

    def load_users(self, file_path):
        self.users = {}
        for line in open(file_path, 'r'):
            username, password = line.strip().split()
            self.add_user(username, password)

    def add_user(self, username, password):
        self.users[username] = User(username, password)


class RequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        self.request.settimeout(self.time_out)
        self.user = None
        try:
            self.log('Connection established')
            if self.authenticate():
                self.user.login()
                self.log('{} logged in'.format(self.user.username))
                while self.user.is_connected:
                    self.send_messages()
                    client_input = self.read()
                    self.user.register_activity()
                    self.process_command(client_input)
            self.log('Connection terminated')
        except socket.timeout:
            self.send_string('timeout:{}'.format(self.time_out))
            self.log('Connection timed out')
        except Exception:
            self.log('Connection lost')

    def finish(self):
        if self.user and self.user.is_connected:
            self.user.logout()
            self.log('{} logged out'.format(self.user.username))

    def authenticate(self):
        while not self.user:
            username = self.read()
            user = self.server.users.get(username)
            if self.ip in user.blocked_connections:
                time_blocked = user.blocked_connections[self.ip]
                time_elapsed = current_time() - time_blocked
                time_left = self.block_time - time_elapsed
                if time_elapsed > self.block_time:
                    user.blocked_connections.pop(self.ip)
                    self.user = user
                else:
                    self.send_string('blocked:{}'.format(time_left))
                    return False
            elif user.is_connected:
                self.send_string('connected')
            else:
                self.user = user
        login_attempts = 0
        while login_attempts < 3:
            self.send_string('password')
            password = self.read()
            if self.user.password == password:
                self.send_string('welcome')
                return True
            login_attempts += 1
        self.send_string(str(self.block_time))
        self.user.blocked_connections[self.ip] = current_time()
        self.log('{} blocked for {} seconds'.format(
            username,
            self.block_time
        ))
        return False


    def process_command(self, command_string):
        command, args = parse_command(command_string)
        if command == 'whoelse':
            self.whoelse()
        elif command == 'whoelsesince':
            try:
                number = int(args[0])
                self.whoelsesince(number)
            except Exception:
                self.send_string('error:args:{}'.format(command))
        elif command == 'broadcast':
            message_string = ' '.join(args)
            self.broadcast(message_string)
        elif command == 'message':
            try:
                usernames = set(
                    args[0] if isinstance(args[0], list) else [args[0]]
                )
                message_string = ' '.join(args[1:])
                self.message(message_string, usernames)
            except Exception:
                self.send_string('error:args:{}'.format(command))
        elif command == 'logout':
            self.send_string('goodbye')
            self.user.logout()
            self.log('{} logged out'.format(self.user.username))
        elif command == 'block':
            print('entered block command unit')
            user_to_be_blocked = args[0]
            self.user.blocked_users.append(user_to_be_blocked)
            print (self.user.blocked_users)
            self.send_string('blocking')
        elif command == 'unblock':
            print('entered unblock command unit')
            user_to_be_unblocked = args[0]
            tmp = self.user.blocked_users.index(user_to_be_unblocked)
            self.user.blocked_users.pop(tmp)
            print (self.user.blocked_users)
            self.send_string('unblocking')
        elif command == 'fetch':
            self.send_string('fetching')
        else:
            self.send_string('error:command:{}'.format(command))

    def send_messages(self):
        messages = self.user.dump_message_queue()
        for message in messages:
            self.send_string(str(message))
        self.send_string('DONE')
        if messages:
            self.log('{} received {} message(s)'.format(
                self.user.username,
                len(messages)
            ))

    def whoelse(self):
        usernames = []
        for user in self.server.users.values():
            if user.is_connected and self.user.username != user.username:
                usernames.append(user.username)
        self.send_string(' '.join(usernames))

    def whoelsesince(self, number):
        usernames = []
        ref_time = current_time()
        for user in self.server.users.values():
            seconds = float(ref_time - user.last_active) 
            if user.is_connected or seconds < number:
                if(user.username != self.user.username):
                    usernames.append(user.username)
        self.send_string(' '.join(usernames))

    def broadcast(self, message):
        self.message(message, self.server.users.keys())

    def message(self, message_string, usernames):
        invalid_usernames, users_messaged = [], 0
        for username in usernames:
            user = self.server.users.get(username)
            if not user:
                invalid_usernames.append(username)
            elif user is not self.user:
                if self.user.username in user.blocked_users:
                    pass
                    # invalid_usernames.append(username)
                else :    
                    message = Message(message_string, self.user)
                    user.add_messeges(message)
                    users_messaged += 1
        self.send_string('sent:{}'.format(''.join(invalid_usernames)))
        self.log('{} sent a message to {} user(s)'.format(
            self.user.username,
            users_messaged
        ))

    def read(self):
        data = self.request.recv(BUFFER_SIZE).strip()
        if not data:
            raise socket.error
        return data

    def send_string(self, string):
        self.request.sendall('{}\n'.format(string))

    def log(self, message):
        print ('[{}] {}: {}'.format(
            current_time_string(),
            self.ip,
            message,
        ))

    @property
    def ip(self):
        return self.client_address[0]

    @property
    def block_time(self):
        return int(os.environ.get('BLOCK_TIME') or 60)

    @property
    def time_out(self):
        return int(os.environ.get('TIME_OUT') or 30 * 60)


if len(sys.argv) > 1:
    ip_address, port_number, block_duration, timeout = ('localhost', int(sys.argv[1]), sys.argv[2], sys.argv[3])
    os.environ['BLOCK_TIME'] = block_duration
    os.environ['TIME_OUT'] = timeout
    server_address = (ip_address, port_number)
    server = Server(server_address, RequestHandler, 'Credentials.txt')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print ('Goodbye!')
    finally:
        server.shutdown()
else:
    print ('Usage: python {} <port> <block_duration> <timeout>'.format(sys.argv[0]))