RATIO                       = 2
N                           = 3
N_OF_NODES                  = 6
TIME_HELLO_INTERVAL         = 2 / RATIO
TIME_DELETE_INTERVAL        = 8 / RATIO
TIME_SUDDEN_OFF_INTERVAL    = 10 / RATIO
TIME_SUDDEN_OFF_DURATION    = 20 / RATIO
LOSS_PROBABILITY            = 0.05
TIME_SIMULATION             = 2 * 60 / RATIO
T_HELLO                     = 0x001
START_PORT                  = 7000

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    B_BLUE = '\33[103m'
    B_YELLOW = '\33[43m'