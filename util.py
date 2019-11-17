import re
import time 

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
    # print(command + ':' + args)
    return command, args


def current_time():
    return int(time.time())


def current_time_string():
    return time.strftime('%m-%d-%yT%H:%M:%S')