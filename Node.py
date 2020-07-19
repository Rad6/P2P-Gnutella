from Utils import *
from time import time, sleep
import sys, enum, random
import multiprocessing, threading
import socket, pickle


class NodeState(enum.Enum):
    findEnoughtNodes = 0
    normal = 1


def cprint(msg, color=bcolors.ENDC, _node=True):
    global node
    if _node:
        print(f"{color}Node {node.id}: {msg}{bcolors.ENDC}")
    else:
        print(f"{color}{msg}{bcolors.ENDC}")

class Node:
    def __init__(self, _id, _ip, _port):
        self.state          = NodeState.findEnoughtNodes
        self.id             = _id
        self.ip             = _ip
        self.port           = _port
        self.lock_all_lists = threading.Lock()
        self.neighbors      = {}
        # self.lock_unidir    = threading.Lock()
        self.unidir         = {}
        # self.lock_tobe      = threading.Lock()
        self.tobe           = {}
        # self.lock_lasts     = threading.Lock()
        self.lasts          = {}
        self.on             = True
        self.createSocket()

    def __str__(self):
        return f"Node {self.id} = [IP: {self.ip}, Port: {self.port}]"
 
    def turnOn(self):
        self.on = True
    
    def turnOff(self):
        self.on = False

    def createHelloPayload(self, _to):
        
        if _to not in self.lasts:
            last_sent = -1
            last_recv = -1
            self.lasts[_to] = {
                'last_sent' : -1,
                'last_recv' : -1,
            }
        else:
            last_sent = self.lasts[_to]['last_sent']
            last_recv = self.lasts[_to]['last_recv']

        payload = {
            'id'                : self.id,
            'ip'                : self.ip,
            'port'              : self.port,
            'type'              : T_HELLO,
            'neighbors'         : list(self.neighbors),
            'last_sent'         : last_sent,
            'last_recv'         : last_recv,
        }

        self.lasts[_to]['last_sent'] = time()

        return payload

    def findIdInLists(self, _id):
        the_list = None
        # with self.lock_all_lists:
        if _id in self.neighbors:
            the_list = self.neighbors
    
        elif _id in self.unidir:
            the_list = self.unidir
    
        elif _id in self.tobe:
            the_list = self.tobe
        return the_list

    def addRecvPayloadToList(self, _payload, the_list):
        _id = _payload['id']

        noicedic = {
            'id' : _id,
            'ip' : _payload['ip'],
            'port' : _payload['port']
        }

        
        if _id not in self.lasts:
            self.lasts[_id] = {
                'last_recv' : time(),
                'last_sent' : -1,
            }
        else:
            self.lasts[_id]['last_recv'] = time()
    
        prev_list = self.findIdInLists(_id)
        if prev_list != None:
            del prev_list[_id]

        the_list[_id] = noicedic


    def parseRecvHello(self, _payload):
        id_recv = _payload['id']
        neighbors_recv = _payload['neighbors']

        if NodeState.findEnoughtNodes == self.state:
            with self.lock_all_lists:
                if self.id in neighbors_recv:
                    self.addRecvPayloadToList(_payload, self.neighbors)

                elif id_recv in self.tobe:
                    self.addRecvPayloadToList(_payload, self.neighbors)
                
                elif id_recv in self.unidir:
                    self.addRecvPayloadToList(_payload, self.unidir)
                
                elif id_recv in self.neighbors:
                    self.addRecvPayloadToList(_payload, self.neighbors)

                else:
                    self.addRecvPayloadToList(_payload, self.unidir)
                
    def createSocket(self):
        self.socket         = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))


node = None
queue = None
t_recv_data =  None
t_send_hello_neighbors = None
t_delete_old_neighbors = None
t_controller = None
t_neighbor_finder = None
e_on = True
e_running = False

def sendData(payload, address, drop_mode=True):
    try:
        if random.randint(1, 20) != 1:
            node.socket.sendto(pickle.dumps(payload), address)
        else:
            cprint(f" a packet is dropped", bcolors.FAIL)
    except:
        cprint(" Exception Accured in sending part of socket", bcolors.FAIL) #!import: Dont log it ----------------------------

def recvData():
    global e_on
    while True:
        e_on.wait()
        try:
            data, address = node.socket.recvfrom(10000)
            obj = pickle.loads(data)
            cprint(f" recved : from {obj['id']}, neighbors: {obj['neighbors']}")
            node.parseRecvHello(obj)
        except:
            cprint(" Exception Accured in recv part of socket", bcolors.FAIL) #!import: Dont log it ----------------------------

def findEnoughtNodes():
    global e_on
    cprint("start trying to find new neighbors", bcolors.OKBLUE)
    with node.lock_all_lists:
        _len = len(list(node.neighbors))
    while  _len < N:
        node.lock_all_lists.acquire()
        e_on.wait()
        if len(list(node.unidir)) != 0:
            chosen = random.sample(list(node.unidir), 1)[0]
            temp = node.unidir[chosen]
            del node.unidir[chosen]
            node.neighbors[chosen] = temp
        else:
            chosen = random.randint(0, N_OF_NODES-1)
            while (chosen in node.neighbors) or (chosen == node.id):
                chosen = random.randint(0, N_OF_NODES-1)
            
            sendData(node.createHelloPayload(chosen), ('localhost', START_PORT + chosen))
            node.tobe[chosen] = {
                'id' : chosen,
                'ip' : 'localhost',
                'port' : START_PORT + chosen
            }
            cprint(f" {chosen} is chosen")

            node.lock_all_lists.release()
            sleep(TIME_DELETE_INTERVAL) # !Important : --------------------------------------- SLEEP------------------------------
            node.lock_all_lists.acquire()

            # if (chosen not in node.unidir) and (chosen not in node.neighbors):
            try:
                del node.tobe[chosen]
            except:
                pass

        _len = len(list(node.neighbors)) 
        node.lock_all_lists.release()
    
    cprint(f" ############ Now becomes {N} negibors : {list(node.neighbors)} ###########",\
     bcolors.OKGREEN)

def helloNeighbors():
    global e_on
    while True:
        with node.lock_all_lists:
            e_on.wait()
            for item in node.neighbors:
                sendData(node.createHelloPayload(\
                    node.neighbors[item]['id']), \
                        (node.neighbors[item]['ip'], node.neighbors[item]['port']))
        sleep(TIME_HELLO_INTERVAL)

def deleteOldNeighbors():
    global t_neighbor_finder, e_on
    while True:
        with node.lock_all_lists:
            e_on.wait()
            del_list = []
            prev_len = len(node.neighbors)
            for _id in node.neighbors:
                if node.lasts[_id]['last_sent'] - node.lasts[_id]['last_recv'] > TIME_DELETE_INTERVAL:
                    del_list.append(_id)
                    cprint(f" Neighbor {_id} is deleted due to TIME_DELETE_INTERVAL", bcolors.WARNING)
            for _id in del_list:
                del node.neighbors[_id]
            if len(node.neighbors) < N and prev_len >= N: # start finding more nodes due to deletes
                t_neighbor_finder = threading.Thread(target=findEnoughtNodes)
                t_neighbor_finder.setDaemon(False)
                t_neighbor_finder.start()
        sleep(TIME_HELLO_INTERVAL)


def controller():
    global queue, t_recv_data, t_send_hello_neighbors, t_delete_old_neighbors, \
        t_controller, e_on, e_running
    while True:
        data = queue.get()
        if data == "off":
            e_on.clear()
            node.socket.close()
            cprint("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~OFFFFF~~~~~~~~~~", bcolors.WARNING)
        
        elif data == "on":
            node.createSocket()
            e_on.set()
            cprint("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ONNNNN~~~~~~~~~~", bcolors.WARNING)


def runNode(_queue, _id, _ip, _port):
    global node, queue, t_recv_data, t_send_hello_neighbors, \
        t_delete_old_neighbors, t_controller, e_on, e_running
    
    queue = _queue
    node = Node(_id, _ip, _port)
    print(node, " is running ... ")

    e_on = threading.Event()
    e_on.set()

    e_running = threading.Event()
    e_running.set()

    # Creating Services Thread
    t_recv_data = threading.Thread(target=recvData)
    t_send_hello_neighbors = threading.Thread(target=helloNeighbors)
    t_delete_old_neighbors = threading.Thread(target=deleteOldNeighbors)
    t_controller = threading.Thread(target=controller)
    t_neighbor_finder = threading.Thread(target=findEnoughtNodes)

    # set deamonity
    t_recv_data.setDaemon(False)
    t_send_hello_neighbors.setDaemon(False)
    t_delete_old_neighbors.setDaemon(False)
    t_neighbor_finder.setDaemon(False)
    t_controller.setDaemon(False)

    # Starting Serveices Thread
    t_recv_data.start()
    t_send_hello_neighbors.start()
    t_delete_old_neighbors.start()
    t_neighbor_finder.start()
    t_controller.start()

    t_controller.join()
    cprint("8888888888888888888 END of runNode 88888888888888888888888888888888")
    # findEnoughtNodes() # starts to find neighbors 





# t_hellowtimer = None
# t_hellowtimer_end = False
# _id = -1

# def foo():
#     global t_hellowtimer_end
#     global _id

#     while True:
#         if t_hellowtimer_end:
#             sleep(20)
#             t_hellowtimer_end = False
#         print(f"{_id} : triggerd")
#         sleep(1)

# def end():
#     sleep(5)
#     global t_hellowtimer_end
#     t_hellowtimer_end = True
#     print("thread is killed")

# def readQueueToOff(queue):
#     global t_hellowtimer_end
#     obj = queue.get()
#     if obj == "off":
#         t_hellowtimer_end = True
#         print("off")
#     else:
#         print("noo")
    
# def gone(id):
#     _id = id
    
#     t_hellowtimer = threading.Thread(target=foo)
#     t_off         = threading.Thread(target=readQueueToOff, args=(queue, ))
#     # t_killer      = threading.Thread(target=end)

#     t_hellowtimer.start()
#     # t_killer.start()
#     t_off.start()

#     t_off.join()
#     # t_killer.join()
#     t_hellowtimer.join()