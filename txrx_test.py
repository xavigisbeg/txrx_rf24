#!/usr/bin/env python
# -*- coding: utf-8 -*-

from txrx_functions import *


def main():
    print("Test on Raspberry Pi")
    state = STATE_TX_MOUNT_USB
    # tx_list_of_frames = [bytearray(b"")]
    # tx_frame_num = 0
    # rx_message_to_add_to_file = b""
    last_state = STATE_FINAL
    while True:
        if state != last_state:
            print(state)
            last_state = state
        # At any time we should return to the init state if the start switch is turned off
        if state != STATE_INIT:
            state = run_st_read_start_switch(state)
        # Transmitter states
        if state == STATE_TX_MOUNT_USB:
            state = run_st_tx_mount_usb()

        elif state == STATE_TX_COPY_FROM_USB:
            state = run_st_tx_copy_from_usb()
            state = STATE_RX_COPY_TO_USB

        elif state == STATE_RX_COPY_TO_USB:
            state = run_st_rx_copy_to_usb()


if __name__ == '__main__':
    main()
