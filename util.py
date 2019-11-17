import re
import time 

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