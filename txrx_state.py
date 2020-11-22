from txrx_functions import *


STATE_FINAL = 0
STATE_INIT  = 1


def main():
    state = STATE_INIT
    while not state == STATE_FINAL:
        if state == STATE_INIT:
            state = run_st_init()
        if state == STATE_COMPRESS_NM:
            state = run_st_init()


if __name__ == '__main__':
    main()
