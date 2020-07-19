import os, threading
import multiprocessing
from Node import runNode
from Utils import *
import random
import time

queues = []
procs = []
sudden_offs = set()
running = True

def randomTermination():
    global N_OF_NODES, sudden_offs, e_end
    while True:
        if not running:
            break
        # time.sleep(TIME_SUDDEN_OFF_INTERVAL)
        e_end.wait(timeout=TIME_SUDDEN_OFF_INTERVAL)
        if not running:
            break
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

def endSimulation():
    global running
    time.sleep(TIME_SIMULATION)
    e_end.set()
    running = False
    for queue in queues:
        queue.put("end")


if __name__ == "__main__":
    for i in range(N_OF_NODES):
        q = multiprocessing.Queue()
        queues.append(q)
        procs.append(multiprocessing.Process(target=runNode, args=(q, i, 'localhost', START_PORT + i)))

    for item in procs:
        item.start()
    
    e_end = threading.Event()
    e_end.clear()

    t_randterminator = threading.Thread(target=randomTermination)
    t_endSimulation = threading.Thread(target=endSimulation)

    t_randterminator.setDaemon(False)

    t_randterminator.start()
    t_endSimulation.start()

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
        