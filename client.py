import getpass
import socket
import sys

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
    fetch                               Fetch messages in message queue
"""


class ChatClient:

    def __init__(self, server_address):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(server_address)
        self.fd = self.socket.makefile()  # convenient for I/O

    def close(self):
        self.fd.close()
        self.socket.close()

    def handle(self):
        self.print_string(START_STRING)
        if self.authenticate():
            self.print_string('Welcome, {} to the greatest messaging application ever!\n'.format(self.username))
            while True:
                self.read_messages()
                command_string = self.get_input('> ')
                if command_string == 'help':
                    self.print_string(HELP_STRING)
                # Default empty commands or `help` to `fetch`
                if not command_string or command_string == 'help':
                    command_string = 'fetch'
                self.send_string(command_string)
                response = self.read_line()
                if response == 'goodbye':
                    break  # terminate connection
                elif response.startswith('sent:'):
                    _, invalid_usernames = response.split(':')
                    if invalid_usernames:
                        self.print_string(
                            'The following username(s) are invalid: '
                            '{}\n'.format(invalid_usernames)
                        )
                elif response.startswith('error:'):
                    _, error_type, command = response.split(':')
                    if error_type == 'command':
                        self.print_string(
                            'Command not found: {}\n'.format(command)
                        )
                    elif error_type == 'args':
                        self.print_string(
                            'Invalid arguments for command: {}. '
                            'Enter `help` for usage.\n'.format(command)
                        )
                elif response == 'fetching':
                    pass
                else:
                    self.print_string('{}\n'.format(response))

    def authenticate(self):
        while True:
            username = self.get_input('username: ')
            if not username:
                continue
            self.send_string(username)
            response = self.read_line()
            if response.startswith('blocked:'):
                blocked, time_left = response.split(':')
                self.print_string(
                    'Logins for {} from this IP address are blocked. Wait'
                    ' {} seconds for block to be lifted.\n'.format(
                        username,
                        time_left
                    )
                )
                return False
            elif response == 'connected':
                self.print_string('User already connected\n')
            else:
                break
        while True:
            password = getpass.getpass('password: ')
            if not password:
                continue
            self.send_string(password)
            response = self.read_line()
            if response == 'welcome':
                self.username = username
                return True
            elif response == 'password':
                pass
            else:
                break
        self.print_string(
            'Logins for {} from this IP address have been blocked'
            ' for {} seconds.\n'.format(username, response)
        )
        return False

    def read_messages(self):
        messages = []
        line = self.read_line()
        while line != 'DONE':
            messages.append(line)
            line = self.read_line()
        if messages:
            self.print_string('{}\n'.format('\n'.join(messages)))

    def read_line(self):
        line = self.fd.readline().strip()
        if line.startswith('timeout:'):
            _, time_out = line.split(':')
            raise socket.timeout(time_out)
        return line

    def send_string(self, string):
        self.socket.sendall('{}\n'.format(string))

    def print_string(self, string):
        sys.stdout.write(string)
        sys.stdout.flush()

    def get_input(self, string):
        self.print_string(string)
        return sys.stdin.readline().strip()


if len(sys.argv) > 2:
    server_ip, server_port = sys.argv[1], int(sys.argv[2])
    server_address = (server_ip, server_port)
    client = ChatClient(server_address)
    try:
        client.handle()
    except socket.timeout as exception:
        print ('Connection timed out after {} seconds'.format(
            exception.message
        ))
    except socket.error:
        print ('Server unreachable')
    except KeyboardInterrupt:
        print ('Goodbye!')
    finally:
        client.close()
else:
    print ('Usage: python {} <server ip> <sever port>'.format(sys.argv[0]))