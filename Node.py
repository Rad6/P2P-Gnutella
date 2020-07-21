from Utils import *
from time import time, sleep
import sys, enum, random, traceback
import multiprocessing, threading
import socket, pickle
import json


def cprint(msg, color=bcolors.ENDC, _node=True):
    global node
    if _node:
        print(f"{color}Node {node.id}: {msg}{bcolors.ENDC}")
    else:
        print(f"{color}{msg}{bcolors.ENDC}")

class Node:
    def __init__(self, _id, _ip, _port):
        self.id             = _id
        self.ip             = _ip
        self.port           = _port
        self.lock_all_lists = threading.Lock()
        self.neighbors      = {}
        self.unidir         = {}
        self.tobe           = {}
        self.lasts          = {}
        self.createSocket()
        self.end_time       = None

    def __str__(self):
        return f"Node {self.id} = [IP: {self.ip}, Port: {self.port}]"
 
    def createHelloPayload(self, _to):
        last_sent = time()

        if _to not in self.lasts:
            self.lasts[_to] = {
                'id'        : _to,
                'ip'        : 'localhost',
                'port'      : START_PORT + _to,
                'last_sent' : last_sent,
                'last_recv' : -1,
                'neighbors' : [],
                'ntimes'    : [],
                'nnsent'    : 1,
                'nnrecv'    : 0,
            }
        else:
            self.lasts[_to]['last_sent'] = last_sent
            self.lasts[_to]['nnsent'] += 1

        payload = {
            'id'                : self.id,
            'ip'                : self.ip,
            'port'              : self.port,
            'type'              : T_HELLO,
            'neighbors'         : list(self.neighbors),
            'last_sent'         : self.lasts[_to]['last_sent'],
            'last_recv'         : self.lasts[_to]['last_recv'],
        }

        return payload

    def findIdInLists(self, _id):
        the_list = None

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
                'id'        : _id,
                'ip'        : _payload['ip'],
                'port'      : _payload['port'],
                'last_recv' : time(),
                'last_sent' : -1,
                'neighbors' : _payload['neighbors'],
                'ntimes'    : [],
                'nnsent'    : 0,
                'nnrecv'    : 1,
            }
        else:
            self.lasts[_id]['last_recv'] = time()
            self.lasts[_id]['neighbors'] = _payload['neighbors']
            self.lasts[_id]['nnrecv'] += 1

    
        prev_list = self.findIdInLists(_id)
        if prev_list != None:
            del prev_list[_id]

        the_list[_id] = noicedic


    def parseRecvHello(self, _payload):
        id_recv = _payload['id']
        neighbors_recv = _payload['neighbors']

        if self.id in neighbors_recv:
            if len(self.neighbors) < N:
                if id_recv not in self.neighbors:
                    self.addRecvPayloadToList(_payload, self.neighbors) # add
                    node.lasts[id_recv]['ntimes'].append([time(), None])
                else:
                    self.addRecvPayloadToList(_payload, self.neighbors) # update     
            elif id_recv in self.neighbors:
                self.addRecvPayloadToList(_payload, self.neighbors) # update
            else:
                self.addRecvPayloadToList(_payload, self.unidir)

        elif id_recv in self.tobe:
            self.addRecvPayloadToList(_payload, self.neighbors)
            node.lasts[id_recv]['ntimes'].append([time(), None])
        
        elif id_recv in self.unidir:
            self.addRecvPayloadToList(_payload, self.unidir)
        
        elif id_recv in self.neighbors:
            self.addRecvPayloadToList(_payload, self.neighbors)

        else:
            self.addRecvPayloadToList(_payload, self.unidir)
            
    def createSocket(self):
        try:
            self.socket         = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.ip, self.port))
        except Exception as e:
            cprint(" *********************** UNABLE TO CREATE SOCKET *********************", \
                bcolors.FAIL)
            raise


    def closeSocket(self):
        self.socket.close()

node = None
queue_from_node = None
queue_to_node = None
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
            cprint(f" send to {address[1] - START_PORT} time : {time()}")
        else:
            cprint(f" a packet is dropped", bcolors.FAIL)
    except Exception:
        cprint(" Exception Accured in sending part of socket", bcolors.FAIL) #!import: Dont log it ----------------------------
        traceback.print_exc()

def recvData():
    global e_on
    while True:

        e_on.wait()
        if not e_running.is_set(): # Safe point to termination
            break

        try:
            data, address = node.socket.recvfrom(10000)
            obj = pickle.loads(data)
            cprint(f" recved : from {obj['id']}, neighbors: {obj['neighbors']} time: {time()}")

            node.lock_all_lists.acquire()
            node.parseRecvHello(obj)
            node.lock_all_lists.release()
        except Exception:
            cprint(" Exception Accured in recv part of socket", bcolors.FAIL) #!import: Dont log it ----------------------------
            traceback.print_exc()
            node.lock_all_lists.release()

def findEnoughtNodes():
    global e_on
    cprint(" start trying to find new neighbors", bcolors.OKBLUE)
    with node.lock_all_lists:
        _len = len(list(node.neighbors))
    while  _len < N:
        node.lock_all_lists.acquire()
        
        e_on.wait()
        if not e_running.is_set(): # Safe point to termination
            node.lock_all_lists.release()
            break
        
        if len(list(node.unidir)) != 0:
            chosen = random.sample(list(node.unidir), 1)[0]
            temp = node.unidir[chosen]
            del node.unidir[chosen]
            node.neighbors[chosen] = temp # !important-------------------------------------- ---------------------------
            node.lasts[temp['id']]['ntimes'].append([time(), None])
        else:
            chosen = random.randint(0, N_OF_NODES-1)
            while (chosen in node.neighbors) or (chosen == node.id):
                chosen = random.randint(0, N_OF_NODES-1)
            
            cprint(f" {chosen} is chosen")
            sendData(node.createHelloPayload(chosen), ('localhost', START_PORT + chosen))
            node.tobe[chosen] = {
                'id' : chosen,
                'ip' : 'localhost',
                'port' : START_PORT + chosen
            }

            node.lock_all_lists.release()
            sleep(TIME_DELETE_INTERVAL) # !Important : --------------------------------------- SLEEP------------------------------
            node.lock_all_lists.acquire()

            try:
                del node.tobe[chosen]
            except:
                pass

        _len = len(list(node.neighbors)) 

        node.lock_all_lists.release()

        if _len >= 3:
            cprint(f" ############ Now becomes {_len} negibors : {list(node.neighbors)} ###########",\
                bcolors.OKGREEN)
            break

def helloNeighbors():
    global e_on
    while True:
       
        node.lock_all_lists.acquire()
        e_on.wait()
        if not e_running.is_set(): # Safe point to termination
            node.lock_all_lists.release()
            break

        for item in node.neighbors:
            sendData(node.createHelloPayload(\
                node.neighbors[item]['id']), \
                    (node.neighbors[item]['ip'], node.neighbors[item]['port']))

        node.lock_all_lists.release()
        sleep(TIME_HELLO_INTERVAL)

def deleteOldNeighbors():
    global t_neighbor_finder, e_on
    while True:
        node.lock_all_lists.acquire()

        e_on.wait()
        if not e_running.is_set(): # Safe point to termination
            node.lock_all_lists.release()
            break

        del_list = []
        prev_len = len(node.neighbors)
        for _id in node.neighbors:
            dur = time() - node.lasts[_id]['last_recv']
            if  dur > TIME_DELETE_INTERVAL:
                del_list.append(_id)
                cprint(f" Neighbor {_id} is deleted due to TIME_DELETE_INTERVAL at last recv {node.lasts[_id]['last_recv']} and dur is {dur}", bcolors.WARNING)
        for _id in del_list:
            node.lasts[_id]['ntimes'][-1][1] = time() # add exit time
            del node.neighbors[_id]
        if len(node.neighbors) < N and prev_len >= N: # start finding more nodes due to deletes
            t_neighbor_finder = threading.Thread(target=findEnoughtNodes)
            t_neighbor_finder.setDaemon(False)
            t_neighbor_finder.start()
        
        node.lock_all_lists.release()
        sleep(TIME_HELLO_INTERVAL)


def motherLoger():
    cprint(" Mother Logger Does its Job")

    final_log = {}

    final_log["id"] = node.id
    final_log["ip address"] = node.ip
    final_log["port"] = node.port

    final_log['Neighbors history'] = []
    for key, value in node.lasts.items():
        if len(value['ntimes']) != 0:
            tmp = {}
            tmp['id'] = value['id']
            tmp['ip address'] = value['ip']
            tmp['port'] = value['port']
            tmp['packets sent'] = value['nnsent']
            tmp['packets recv'] = value['nnrecv']
            final_log['Neighbors history'].append(tmp)

    final_log['Current valid neighbors'] = []
    for key, value in node.neighbors.items():
        tmp = {}
        tmp['id'] = value['id']
        tmp['ip address'] = value['ip']
        tmp['port'] = value['port']
        final_log['Current valid neighbors'].append(tmp)

    final_log['Nodes accessibilities'] = []
    for key, value in node.lasts.items():
        if len(value['ntimes']) != 0:
            tmp = {}
            acc_time = 0
            for each in value['ntimes']:
                if each[1] == None:
                    acc_time += ( node.end_time - each[0] )
                else:
                    acc_time += ( each[1] - each[0] )
            tmp['id'] = value['id']
            tmp['ip address'] = value['ip']
            tmp['port'] = value['port']
            tmp['accessibility'] = (acc_time / TIME_SIMULATION)*100
            final_log['Nodes accessibilities'].append(tmp)

    final_log['Current uni list'] = []
    for key, value in node.unidir.items():
        tmp = {}
        tmp['id'] = value['id']
        tmp['ip address'] = value['ip']
        tmp['port'] = value['port']
        final_log['Current uni list'].append(tmp)

    final_log['Current tobe list'] = []
    for key, value in node.tobe.items():
        tmp = {}
        tmp['id'] = value['id']
        tmp['ip address'] = value['ip']
        tmp['port'] = value['port']
        final_log['Current tobe list'].append(tmp)
    
    file_name = 'node' + str(node.id) + '.json'
    with open(file_name, 'w') as f:
        json.dump(final_log, f, indent=4)


def controller():
    global queue_from_node, queue_to_node, t_recv_data, t_send_hello_neighbors, t_delete_old_neighbors, \
        t_controller, e_on, e_running
    while True:
        data = queue_from_node.get()
        if data == "off":
            e_on.clear()
            node.closeSocket()
            cprint(" ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~OFFFFF~~~~~~~~~~", bcolors.WARNING)
        
        elif data == "on":
            node.createSocket()
            e_on.set()
            cprint(" ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ONNNNN~~~~~~~~~~", bcolors.WARNING)

        elif data == "end":
            node.end_time = time()
            e_running.clear()
            e_on.set() # releasing those are waiting
            node.closeSocket()
            # TODO: add logs to file

            with node.lock_all_lists:
                motherLoger()

            cprint(" 8888888888888888888 END of runNode 88888888888888888888888888888888")
            queue_to_node.put("done")
            break

def runNode(_queue1, _queue2, _id, _ip, _port):
    global node, queue_from_node, queue_to_node, t_recv_data, t_send_hello_neighbors, \
        t_delete_old_neighbors, t_controller, e_on, e_running
    
    queue_from_node = _queue1
    queue_to_node = _queue2
    node = Node(_id, _ip, _port)
    print(node, " is running ... ")

    e_on = threading.Event()
    e_on.set()

    e_running = threading.Event()
    e_running.set()

    # Creating Services Thread
    t_recv_data = threading.Thread(target=recvData)
    t_send_hello_neighbors = threading.Thread(target=helloNeighbors)
    t_delete_old_neighbors = threading.Thread(target=deleteOldNeighbors, name=f"deletneighbors = [{_id}], ")
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