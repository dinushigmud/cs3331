
import os
import socket
import SocketServer
import sys
import user
import re
import time 

from Queue import Queue

BUFFER_SIZE = 1024

"""
Helper Functions 
"""

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
        self.blocked_login_users = {}    #keeps track of connections blocked when dealing with authentication
        self.blocked_users = []          #keeps track of users blocked(used for the implementation of block and unblock commands)
        self.message_queue = Queue()     #keeps track of the messeges yet to be viewed by the user 

    def login(self):
        self.is_connected = True
        #login is the first user active command
        self.register_last_activity()

    #resets the .last_active variable everytime the user is active 
    #called by the server 
    def register_last_activity(self):
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

"""
This class initiated the Server connection and loads_the necessary information from Credentials.txt
"""

class Server(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, request_handler, user_file_path):
        SocketServer.TCPServer.__init__(self, server_address,request_handler)
        self.load_users(user_file_path)
        self.daemon_threads = True

    # read line by line of Credentials.txt 
    # each line is split to get the username and password 
    # which is hence passed to the User class to subsequentially create a User object
    def load_users(self, file_path):
        self.users = {}
        for line in open(file_path, 'r'):
            username, password = line.strip().split()
            self.add_user(username, password)

    def add_user(self, username, password):
        self.users[username] = User(username, password)

"""
This class handles literally everything from processing the commands to handling authentication 
"""
class RequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        self.request.settimeout(self.time_out)
        self.user = None
        try:
            #make sure the server can be reached if so 'connection established'
            self.log('Connection established')
            #deal first with authetication 
            if self.authenticate():
                #if user is authenticated then login the user
                self.user.login()
                self.log('{} logged in'.format(self.user.username))
                #whilst the user is loggedin continue to read user input commands and process them
                while self.user.is_connected:
                    self.send_messages()
                    c_input = self.read()
                    #for each command entered that is s user_last active time
                    self.user.register_last_activity()
                    #process each command
                    self.process_command(c_input)
            self.log('Connection terminated')
        except socket.timeout:
            self.send_string('timeout:{}'.format(self.time_out))
            self.log('Connection timed out')
        except Exception:
            self.log('Connection lost')
    """
    Function related to authentication of usser.
    The function will handle authentication by checking if the user input password is the 
    same as the password from User.password
    User gets three chances to attempt inputting of the correct password before blocking the
    user for 'BLOCK_TIME'
    Function returns True if authenticated and False if not 
    """
    def authenticate(self):
        while not self.user:
            uname = self.read()
            user = self.server.users.get(uname)
            #first makesure the self.user is not blocked due to multiple failed login attempts
            if self.connection in user.blocked_login_users:
                #if blocked --->
                t_blocked = user.blocked_login_users[self.connection]
                t_elapsed = current_time() - t_blocked
                t_left = self.block_time - t_elapsed
                #first check if the 'BLOCK_TIME' has elapsed since user was blocked 
                if t_elapsed > self.block_time:
                    #if elapsed recognise the user and prompt to enter password 
                    user.blocked_login_users.pop(self.connection)
                    self.user = user
                else:
                    #if not elapsed send a message to client indicating that the user is blocked 
                    # and the time left till block will be lifted such that the client can display 
                    # a corresponding message
                    self.send_string('blocked:{}'.format(t_left))
                    return False
            #else if check if the user is already connected
            elif user.is_connected:
                #if so send a message to client indicating that the user is alread connected so that
                #the client can display a corresponding message
                self.send_string('connected')
            else:
                self.user = user
        #having setup self.user we can now check if the password inserted by the user is indeed correct
        login_attempts = 0
        while login_attempts < 3:
            self.send_string('password')
            password = self.read()
            #if correct password return True
            if self.user.password == password:
                self.send_string('welcome')
                return True
            #else present another chance till login_attempts does not exceed three
            login_attempts += 1
        #send a message to client to indicate that the current user trying to login has been blocked
        self.send_string(str(self.block_time))
        #login has failed so maksure to enter the current time to user.blocked_login_users 
        # to keep track of when the user was firs blocked
        self.user.blocked_login_users[self.connection] = current_time()
        #server side log
        self.log('{} blocked for {} seconds'.format(uname,self.block_time))
        return False

    """
    This function is the main thinking box on the server side---> processing the commands 
    inputted by the user
    commands : whoelse, whoelsesince, message and broadcast are processed to redirect to another
    function that will execute the command
    commands : fetch, logout, block and unblock are executed in this function itself since 
    these commands only require changing of certain variable values and uodating User.fields and such
    """
    def process_command(self, command_string):
        #parse_commands seperates the main command (command) and the rest of the args (args)
        #basic processing is done using the main command 
        command, args = parse_command(command_string)
        #command = "whoelse"
        if command == 'whoelse':
            self.whoelse()
        #command = "whoelsesince"
        elif command == 'whoelsesince':
            try:
                number = int(args[0])
                self.whoelsesince(number)
            except Exception:
                self.send_string('error:args:{}'.format(command))
        #command = "broadcast"
        elif command == 'broadcast':
            message_string = ' '.join(args)
            self.broadcast(message_string)
        #command = "message"
        elif command == 'message':
            try:
                usernames = set(args[0] if isinstance(args[0], list) else [args[0]])
                message_string = ' '.join(args[1:])
                self.message(message_string, usernames)
            except Exception:
                self.send_string('error:args:{}'.format(command))
        #command = "logout"
        elif command == 'logout':
            #in processing this command we acces the User.logout function
            self.send_string('goodbye')
            self.user.logout()
            self.log('{} logged out'.format(self.user.username))
        #command = "block"
        elif command == 'block':
            #in processing this command the user is added to the user.blocked_users list
            print('entered block command unit')
            user_to_be_blocked = args[0]
            self.user.blocked_users.append(user_to_be_blocked)
            print (self.user.blocked_users)
            self.send_string('blocking')
        #command = "unblock"
        elif command == 'unblock':
            #in processing this command the user inidcated is removed from the User.blocked_users list
            print('entered unblock command unit')
            user_to_be_unblocked = args[0]
            tmp = self.user.blocked_users.index(user_to_be_unblocked)
            self.user.blocked_users.pop(tmp)
            print (self.user.blocked_users)
            self.send_string('unblocking')
        #command = "fetch " ---> used to deal with whitespace and empty command inputs
        #fetch command is first processed in the client side 
        elif command == 'fetch':
            self.send_string('fetching')
        #all other inputs become unknown commands 
        else:
            self.send_string('error:command:{}'.format(command))

    #this function takes all the messages stored in User.message_queue and sends them to the client side for display
    def send_messages(self):
        messages = self.user.dump_message_queue()
        for message in messages:
            self.send_string(str(message))
        #after sending the messages ---> string 'DONE' is sent to indicate the end of the message_queue to the client
        self.send_string('DONE')
        #server side log
        if messages:
            self.log('{} received {} message(s)'.format(self.user.username,len(messages)))

    #processing of the whoelse function
    def whoelse(self):
        usernames = []
        #goes through all the users stored in the server.users
        for user in self.server.users.values():
            #checks whethet they are currently logged in as inidcated by Useer.is_connected and 
            # if they are not the current user itself then append to list usernames
            if user.is_connected and self.user.username != user.username:
                usernames.append(user.username)
        #return usernames list as a string 
        self.send_string(' '.join(usernames))

    #processing of the whoelsesince function
    #similar processing to whoelse, except looking into the time passed in as 'number'
    def whoelsesince(self, number):
        usernames = []
        ref_time = current_time()
        for user in self.server.users.values():
            #check if the user_last was active in the time frame indicated by number 
            #if so continue to process similar to whoelse
            seconds = float(ref_time - user.last_active) 
            if user.is_connected or seconds < number:
                if(user.username != self.user.username):
                    usernames.append(user.username)
        self.send_string(' '.join(usernames))

    #makes use of the message function by sending the message to all users in the server
    def broadcast(self, message):
        self.message(message, self.server.users.keys())

    #This function is written with the intention of being used for broadcast as well
    #thereby the function takes in a list of users to send the message to 
    def message(self, message_string, usernames):
        invalid_usernames, users_messaged = [], 0
        #iterates through each username 
        for username in usernames:
            user = self.server.users.get(username)
            if not user:
                #if user does not exist error handling ensued
                invalid_usernames.append(username)
                #else makesure message is not being sent to the sender
            elif user is not self.user:
                #makesure the sender is not blocked by the recepient
                if self.user.username in user.blocked_users:
                    pass
                    # invalid_usernames.append(username)
                #send message
                else :    
                    #first initialize  Message
                    message = Message(message_string, self.user)
                    #add message to the receipients User.messge_queue
                    user.add_messeges(message)
                    users_messaged += 1
        self.send_string('sent:{}'.format(''.join(invalid_usernames)))
        self.log('{} sent a message to {} user(s)'.format(self.user.username,users_messaged))

    def read(self):
        # self.request is the TCP socket connected to the client
        #.recv used to reveive data
        data = self.request.recv(BUFFER_SIZE).strip()
        if not data:
            raise socket.error
        return data

    def send_string(self, string):
        # self.request is the TCP socket connected to the client
        #.recv used to send data
        self.request.sendall('{}\n'.format(string))

    #server side log indicating the commands processed on the server side
    def log(self, message):
        print ('[{}] {}: {}'.format(current_time_string(),self.connection,message,))

    @property
    def connection(self):
        return self.client_address[0]

    @property
    def block_time(self):
        return int(os.environ.get('BLOCK_TIME') or 60)

    @property
    def time_out(self):
        return int(os.environ.get('TIME_OUT') or 30 * 60)

# main execution on server side according to assignment specifications
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