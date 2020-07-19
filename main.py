import os, threading
import multiprocessing
from Node import runNode
from Utils import *
import random
import time

queues = []
procs = []
sudden_offs = set()

def randomTermination():
    global N_OF_NODES, sudden_offs
    while True:
        time.sleep(TIME_SUDDEN_OFF_INTERVAL)
        rint = random.randint(0, N_OF_NODES-1)
        while rint in sudden_offs:
            rint = random.randint(0, N_OF_NODES-1)
        sudden_offs.add(rint)
        queues[rint].put("off")
        t_timer_oner = threading.Timer(TIME_SUDDEN_OFF_DURATION, turnOn, [rint, ])
        t_timer_oner.setDaemon(False)
        t_timer_oner.start()
        print(f"Main  : sends off to node {rint}")

def turnOn(_id):
    queues[_id].put("on")
    sudden_offs.remove(_id)
    
if __name__ == "__main__":
    for i in range(N_OF_NODES):
        q = multiprocessing.Queue()
        queues.append(q)
        procs.append(multiprocessing.Process(target=runNode, args=(q, i, 'localhost', START_PORT + i)))

    for item in procs:
        item.start()
    
    t_randterminator = threading.Thread(target=randomTermination)
    t_randterminator.setDaemon(True)

    t_randterminator.start()

    # t_randterminator.join()
    for item in procs:
        item.join()

    print("end of main proc")
    


# if __name__ == "__main__":
#     N = 1

#     for i in range(1, N + 1):
#         pid = os.fork()
#         if pid == 0:
#             os.system(f'python Node.py {i} localhost { 8080 + i }')
#             break

#     for i in range(1, N + 1):
#         try:
#             os.wait()
#         except:
#             pass
        