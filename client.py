#declare imports
import getpass
import socket
import sys

#declare printable strings for UI ease of use
START_STRING = """\
------------------------------------------------------------------
You are entering cs3331 assignment chat room!
"""
HELP_STRING = """\
Commands:
    whoelse                             Display users curently online
    whoelsesince <seconds>              Display users online in the last number of seconds
    broadcast <message>                 Send message to all users
    message <user> <message>            Send message to user
    logout                              Logout from chat server
    block <user>                        Block a user 
    unblock <user>                      Unblock a user
    *simply ENTER to see any messages in queue to be viewed
"""


class Client:

    def __init__(self, server_address):
        # Create a socket (SOCK_STREAM means a TCP socket)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to server 
        self.socket.connect(server_address)
        self.fd = self.socket.makefile()  # convenient because now we don't need to use raw recv() calls 
                                          #can use fd.readline().strip() per example

    def close(self):
        self.fd.close()
        self.socket.close()

    '''
    This function works towards handling the command prompt/ UI for the user
    Start off with the WELCOME_STRING (once authenticated) and directs to an unending while loop() where
        - command input by user is read and processes in this function
        - help : prints out HELP_STRING to provide prompt usage
        - fetch : displays all messages in the User.message_queue
        - other command_lines are redirected to the serverSocket via send_string
    '''
    def handle(self):
        self.print_string(START_STRING)
        if self.authenticate():
            self.print_string('Welcome, {} to the greatest messaging application ever!\n'.format(self.username))
            while True:
                self.receive_messeges()
                command_string = self.get_input('> ')
                if command_string == 'help':
                    self.print_string(HELP_STRING)
                # Default empty commands or `help` become `fetch` commands
                if not command_string or command_string == 'help':
                    command_string = 'fetch'

                # Dealing with  command line inputs ---> sent to the server to process
                #                                   ---> received errors displayed to users   
                self.send_string(command_string)
                retval = self.read_line()
                if retval == 'goodbye':
                    break  
                elif retval.startswith('sent:'):
                    _, invalid_usernames = retval.split(':')
                    if invalid_usernames:
                        self.print_string('The following username(s) are invalid: {}\n'.format(invalid_usernames))
                elif retval.startswith('error:'):
                    _, error_type, command = retval.split(':')
                    if error_type == 'command':
                        self.print_string('Command not found: {}\n'.format(command))
                    elif error_type == 'args':
                        self.print_string('Error: Invalid command: {}. Enter `help` for usage.\n'.format(command))
                elif retval == 'fetching':
                    pass
                else:
                    self.print_string('{}\n'.format(retval))

    '''
    Deals with the prompting of user authentication details including username and first attempt at password
    Error message displays related to authentication also handled in this function, however the actual authentication 
    happens in server.py and thereby is explained there
    '''
    def authenticate(self):
        while True:
            username = self.get_input('username: ')
            if not username:
                continue
            self.send_string(username)
            retval = self.read_line()
            if retval.startswith('blocked:'):
                blocked, time_left = retval.split(':')
                self.print_string('Logins for {} have been blocked due to multiple failed logins. Please try again later.'
                    ' {} seconds for block to be lifted.\n'.format(username,time_left))
                return False
            elif retval == 'connected':
                self.print_string('User already connected\n')
            else:
                break
        while True:
            password = getpass.getpass('password: ')
            if not password:
                continue
            self.send_string(password)
            retval = self.read_line()
            if retval == 'welcome':
                self.username = username
                return True
            elif retval == 'password':
                pass
            else:
                break
        self.print_string('Logins for {} have been blocked due to multiple failed logins for {} seconds.\n'.format(username, retval))
        return False


    #------------------------------------------------------------------------------------------------
    #Supporting + Helper functions 
    #------------------------------------------------------------------------------------------------
   
    """
    The server sends messages from users via send_messeges function which is hence recieved at this function
    End of the messeges indicated by 'DONE'
    The received messeges are temporaily stored in messeges list before being displayed upon enter 
    """
    def receive_messeges(self):
        messages = []
        line = self.read_line()
        while line != 'DONE':
            messages.append(line)
            line = self.read_line()
        if messages:
            self.print_string('{}\n'.format('\n'.join(messages)))

    """
    Helper function to read off the clientSocket connected for ease of use via fd instead or raw.recv() call
    """
    def read_line(self):
        line = self.fd.readline().strip()
        if line.startswith('timeout:'):
            _, time_out = line.split(':')
            raise socket.timeout(time_out)
        return line

    """
    Helper function to send data in the form of a string
    Mostly used on the client side to send through the command prompts entered by user to the server
    """
    def send_string(self, string):
        self.socket.sendall('{}\n'.format(string))

    """
    Helper function to print string to sys-stdout
    """
    def print_string(self, string):
        sys.stdout.write(string)
        sys.stdout.flush()

    """
    Helper function to obtain input from sys-stdin
    """
    def get_input(self, string):
        self.print_string(string)
        return sys.stdin.readline().strip()

"""
cs3331 assignment requirements:
    If you use Python:
    python client.py server_IP server_port
    the main function takes in the arguments accordingly 
    the code is written to support basic python
"""
if len(sys.argv) > 2:
    server_ip, server_port = sys.argv[1], int(sys.argv[2])
    server_address = (server_ip, server_port)
    client = Client(server_address)
    try:
        client.handle()
    except socket.timeout as exception:
        print ('Connection timed out after {} seconds'.format(exception.message))
    except socket.error:
        print ('Server unreachable')
    except KeyboardInterrupt:
        print ('Goodbye!')
    finally:
        #socket shut down
        client.close()
else:
    print ('Usage: python {} <server ip> <sever port>'.format(sys.argv[0]))