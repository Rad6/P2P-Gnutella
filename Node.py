from Utils import *
from time import time

class Node:
    def __init__(self, _id, _ip, _port):
        self.id         = _id
        self.ip         = _ip
        self.port       = _port
        self.neighbors  = {}
        self.on         = True
    
    def __str__(self):
        return f"Node {self.id} ."
 
    def turnOn(self):
        self.on = True
    
    def turnOff(self):
        self.on = False

    def __createHelloPayload(self, _to):
        payload = {
            'id'                : self.id,
            'ip'                : self.ip,
            'port'              : self.port,
            'type'              : T_HELLO,
            'neighbors_list'    : self.neighbors,
            'last_sent'         : self.neighbors[_to].last_sent,
            'last_recv'         : self.neighbors[_to].last_recv,
        }
        return payload

    def doNeighborHello(self, _payload):
        new_neighbor = {
            'id'        : _payload['id'],
            'ip'        : _payload['ip'],
            'port'      : _payload['port'],
            'last_recv' : time(),
        }
        self.neighbors[new_neighbor[id]] = new_neighbor

if __name__ == "__main__":
    node = Node(1)
    print(node)