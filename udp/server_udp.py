# Sample code for Multi-Threaded Server
#Python 3
# Usage: python3 UDPserver3.py
#coding: utf-8
from socket import *
import threading
import time
import datetime as dt

#Server will run on this port
serverPort = 13561
t_lock=threading.Condition()
#will store clients info in this list
blocks=[]
block_time=[]
clients=[]
auth_users=[]
auth_pwds=[]
# would communicate with clients after every second
UPDATE_INTERVAL= 1
BLOCK_DURATION = 60
TIMEOUT = 100
timeout=False


def recv_handler():
    global t_lock
    global clients
    global blocks
    global block_time
    global auth_users
    global auth_pwds
    global clientSocket
    global serverSocket
    print('Server is ready for service')
    while(1):
        
        message, clientAddress = serverSocket.recvfrom(2048)
        #received data from the client, now we know who we are talking with
        message = message.decode()
        command = message.split(',')

        #get lock as we might me accessing some shared data structures
        with t_lock:
            currtime = dt.datetime.now()
            date_time = currtime.strftime("%d/%m/%Y, %H:%M:%S")
            print('Received request from', clientAddress[0], 'listening at', clientAddress[1], ':', message, 'at time ', date_time)

            if (len(command) == 3 and command[0] == 'auth'):
                if(command[1] in blocks):
                    tmp = blocks.index(command[1])
                    print(blocks)
                    block_start = block_time[tmp]
                    duration = currtime - block_start
                    print(duration.total_seconds())
                    if(duration.total_seconds() < BLOCK_DURATION):
                        serverMessage = 'Your account is blocked due to multiple login failures. Please try again later'
                    else :
                        bool_tmp = auth_subscriber(command[1], command[2])
                        if(bool_tmp) :
                            clients.append([command[1], clientAddress, currtime])
                            print(clients)
                            serverMessage="Authentication successful"
                        else:
                            serverMessage="Invalid Password. Please try again"
                        block_time.pop(tmp)
                        blocks.pop(tmp)
                        print('block_removal entered')
                        print(blocks)
                else :
                    bool_tmp = auth_subscriber(command[1], command[2])
                    if(bool_tmp) :
                        clients.append([command[1], clientAddress, currtime])
                        print(clients)
                        serverMessage="Authentication successful"
                    else:
                        serverMessage="Invalid Password. Please try again"
            elif(len(command) == 2 and command[0] == 'block'):
                blocks.append(command[1])
                block_time.append(currtime) 
                serverMessage="Block successful"
            elif(len(command) == 3 and command[0] == 'message'):
                message_receipient = command[1]
                receipient= get_client(message_receipient)
                print(receipient[1])
                clientSocket.sendto(command[2].encode(), receipient[1])
            elif(len(command) == 2 and command[0] == 'whoelsesince'):
                serverMessage = get_clients_list_since(int(command[1]),clientAddress )
            elif(command[0] == 'whoelse'):
                serverMessage = get_clients_list(clientAddress)
            else:
                serverMessage="Unknown command, send Subscribe or Unsubscribe only"
            #send message to the client
            serverSocket.sendto(serverMessage.encode(), clientAddress)
            #notify the thread waiting
            t_lock.notify()



def send_handler():
    global t_lock
    global clients
    global blocks
    global block_time
    global auth_users
    global auth_pwds
    global clientSocket
    global serverSocket
    global timeout
    #go through the list of the subscribed clients and send them the current time after every 1 second
    while(1):
        #get lock
        with t_lock:
            for i in clients:
                client_name = i[0]
                client_address = i[1]
                client_last_active_dt = i[2]

                currtime =dt.datetime.now()
                date_time = currtime.strftime("%d/%m/%Y, %H:%M:%S")
                if((currtime - client_last_active_dt).total_seconds() > TIMEOUT):
                    message = 'TIMEOUT INITIATED' 
                    clientSocket.sendto(message.encode(), client_address)
                    print('Sending time to', i[0], 'listening at', i[1], 'at time ', date_time)
            #notify other thread
            t_lock.notify()
        #sleep for UPDATE_INTERVAL
        time.sleep(UPDATE_INTERVAL)


def auth_setup():
    filepath = 'Credentials.txt'
    with open(filepath) as fp:
        line = fp.readline()
        while line:
            cred = line.split()
            auth_users.append(cred[0])
            auth_pwds.append(cred[1])
            line = fp.readline()

def get_auth_index(username):
    return auth_users.index(username)

def auth_subscriber(username, password):
    if username in auth_users:
        auth_index = get_auth_index(username)
        if (password == auth_pwds[auth_index]):
            return True
        return False
    return False

def find_client_by_client_address(clientAddress):
    for client in clients:
        if (client[1] == clientAddress):
            return client

def find_client_by_username(username):
    for client in clients:
        if (client[0] == username ):
            return client

def get_clients_list(clientAddress):
    client_list = ''
    for client in clients:
        if(client[1] != clientAddress):
            client_list = client_list + client[0]
            print(client_list)
    return client_list

def get_clients_list_since(since_time, clientAddress):
    client_list = ''
    for client in clients:
        print(client)
        duration = dt.datetime.now() - client[2]
        if(duration.total_seconds() < since_time and client[1] != clientAddress):
            client_list = client_list + client[0]
    return client_list

def get_client(message_receipient):
    for client in clients:
        if(client[0] == message_receipient):
            return client


#we will use two sockets, one for sending and one for receiving
clientSocket = socket(AF_INET, SOCK_STREAM)
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
serverSocket.bind(('localhost', serverPort))
auth_setup()
    #serverSocket.close()

recv_thread=threading.Thread(name="RecvHandler", target=recv_handler)
recv_thread.daemon=True
recv_thread.start()

send_thread=threading.Thread(name="SendHandler",target=send_handler)
send_thread.daemon=True
send_thread.start()

#this is the main thread
while True:
    time.sleep(0.1)
