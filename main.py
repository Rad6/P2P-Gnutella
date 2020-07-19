import os, threading
import multiprocessing
from Node import runNode
from Utils import *
import random
import time

queues_main_to_procs = []
queues_procs_to_main = []
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
        queues_main_to_procs[rint].put("off")
        t_onner = threading.Thread(target=turnOn, args=(rint,))
        # t_onner.setDaemon(False)
        t_onner.start()
        print(f"Main  :  sends off to node {rint}")

def turnOn(_id):
    e_end.wait(TIME_SUDDEN_OFF_DURATION)
    queues_main_to_procs[_id].put("on")
    sudden_offs.remove(_id)

def endSimulation():
    global running
    time.sleep(TIME_SIMULATION)
    e_end.set()
    running = False
    for queue in queues_main_to_procs:
        queue.put("end")


if __name__ == "__main__":
    for i in range(N_OF_NODES):
        q1 = multiprocessing.Queue()
        q2 = multiprocessing.Queue()
        queues_main_to_procs.append(q1)
        queues_procs_to_main.append(q2)
        procs.append(multiprocessing.Process(target=runNode, args=(q1, q2, i, 'localhost', START_PORT + i)))

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
    # for item in procs:
    #     item.join()

    for i in range(N_OF_NODES):
        msg = queues_procs_to_main[i].get()
        if msg == "done":
            procs[i].terminate()
        else:
            print("Unknown message from proc " + str(i))

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
        