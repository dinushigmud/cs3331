#Python 3
#Usage: python3 UDPClient3.py localhost 12000
#coding: utf-8
from socket import *
import sys

#Server would be running on the same host as Client
serverName = sys.argv[1]
serverPort = int(sys.argv[2])
clientSocket = socket(AF_INET, SOCK_STREAM)

attempts = []

def auth_first_attempt():
    message = input("Username: ")
    username =  message
    message = input("Password: ")
    password =  message
    client_command = 'auth,' + username + ',' + password
    clientSocket.sendto(client_command.encode(), (serverName, serverPort))
    receivedMessage, serverAddress = clientSocket.recvfrom(2048)
    if(receivedMessage.decode() == 'Your account is blocked due to multiple login failures. Please try again later'):
        print (receivedMessage.decode())
    elif(receivedMessage.decode() == 'Authentication successful'):
        print("Welcome to the greatest messaging application ever!")
        command_prompt()
    else:
        print('Invalid password. Please try again')
        attempts.append('attempt')
        auth_reattempt(username)

def auth_reattempt(username):
    if (len(attempts)==3):
        attempts.clear()
        client_command = 'block,' + username 
        clientSocket.sendto(client_command.encode(), (serverName, serverPort))
        receivedMessage, serverAddress = clientSocket.recvfrom(2048)
        if (receivedMessage.decode() == 'Block successful') :
            print('Invalid password. Your account has been blocked. Please try again later')
        clientSocket.close()
        return
    
    message = input('Password: ')
    password =  message
    client_command = 'auth,' + username + ',' + password
    clientSocket.sendto(client_command.encode(), (serverName, serverPort))
    receivedMessage, serverAddress = clientSocket.recvfrom(2048)
    if(receivedMessage.decode() == 'Your account is blocked due to multiple login failures. Please try again later'):
        print (receivedMessage.decode())
    elif(receivedMessage.decode() == 'Authentication successful'):
        print("Welcome to the greatest messaging application ever!")
        command_prompt()
    else:
        print('Invalid password. Please try again')
        attempts.append('attempt')
        auth_reattempt(username)

def command_prompt():
    while(1):
        message = input('commands:{ message <user> <message>, broadcast <message>, whoelse, whoelsesince <time>, block <user>, unblock <user>, logout }')
        command = message.split()

        if(len(command) == 3 and command[0] == 'message'):
            client_command = 'message,' + command[1]+ ',' + command[2]
        elif(len(command) == 2 and command[0] == 'broadcast'):
            client_command = 'broadcast,' + command[1]
        elif(len(command) == 2 and command[0] == 'whoelsesince'):
            client_command = 'whoelsesince,' + command[1]
        elif(len(command) == 2 and command[0] == 'block'):
            client_command = 'block_user,' + command[1]
        elif(len(command) == 2 and command[0] == 'unblock'):
            client_command = 'unblock_user,' + command[1]
        elif(command[0] == 'whoelse'):
            client_command = 'whoelse,' 
        else:
            client_command = 'logout'

        clientSocket.sendto(client_command.encode(), (serverName, serverPort))
        receivedMessage, serverAddress = clientSocket.recvfrom(2048)
        if(receivedMessage.decode() == 'TIMEOUT INITIATED'):
            print('Timeout')
            clientSocket.close()
            return
        else:
            print (receivedMessage.decode())
        

auth_first_attempt()
