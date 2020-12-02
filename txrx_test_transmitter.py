#!/usr/bin/env python
# -*- coding: utf-8 -*-

from txrx_utils import *
from txrx_functions import *
import time
import os


# ------------ Main Function ------------ #

def main():
    print("Test on Transmitter")
    # Initialization of variables
    # state = STATE_TX_COMPRESS
    state = STATE_TX_CREATE_FRAMES_TO_SEND

    tx_list_of_frames = [bytearray(b"")]
    tx_frame_num = 0

    rx_previous_cnt = -1
    rx_list_received_payload = list()

    temp_list_time_between_send = list()
    temp_list_nb_retries = list()
    temp_last_frame_num = -1
    temp_cnt_retries = 0
    t1 = time.time()

    while True:
        # At any time we should return to the init state if the start switch is turned off
        if state != STATE_INIT:
            state = run_st_read_start_switch(state)

        # Common states
        if state == STATE_FINAL:
            pass  # In the final state, we are stuck (unless the start switch if turned OFF)

        elif state == STATE_INIT:
            state = run_st_read_start_switch(state)

        elif state == STATE_READ_SWITCHES:
            state = run_st_read_switches()

        # Transmitter states
        elif state == STATE_TX_MOUNT_USB:
            # stuck here until the USB is detected and mounted
            state = run_st_tx_mount_usb()

        elif state == STATE_TX_COPY_FROM_USB:
            state = run_st_tx_copy_from_usb()

        elif state == STATE_TX_COMPRESS:
            state = run_st_tx_compress()

        elif state == STATE_TX_CREATE_FRAMES_TO_SEND:
            # state, tx_list_of_frames = run_st_tx_create_frames()

            tx_list_of_frames = [create_header(i) + i.to_bytes(31, "big") for i in range(10_000)]
            state = STATE_TX_TRANSMISSION_INIT

            print(f"Number of messages: {len(tx_list_of_frames)}")

        elif state == STATE_TX_TRANSMISSION_INIT:
            state, tx_frame_num = run_st_tx_transmission_init()

        elif state == STATE_TX_TRANSMISSION_SEND_MSG:
            if temp_last_frame_num != tx_frame_num:
                temp_last_frame_num = tx_frame_num
                temp_cnt_retries = 0
                t1 = time.time()

            state, tx_frame_num = run_st_tx_transmission_send_msg(tx_list_of_frames, tx_frame_num)

            if temp_last_frame_num != tx_frame_num:
                t2 = time.time()
                temp_list_time_between_send.append(t2-t1)
                temp_list_nb_retries.append(temp_cnt_retries)
            temp_cnt_retries += 1

        elif state == STATE_TX_TRANSMISSION_SEND_EOT:
            state = run_st_tx_transmission_send_eot()

            if state == STATE_FINAL:  # Creation of the report
                print("Transmission done!!")

                num = 0
                name_of_file = "report_tx_"
                while os.path.exists(name_of_file + str(num) + ".csv"):
                    num += 1
                name_of_file += str(num) + ".csv"

                csv = "Number of sent message; Time between each sending; Number of retries\n"
                for i in range(len(temp_list_time_between_send)):
                    csv += str(i) + "; " + str(temp_list_time_between_send[i]) \
                           + "; " + str(temp_list_nb_retries[i]) + "\n"
                with open(name_of_file, "w") as f:
                    f.write(csv)
                exit(0)

        # Receiver states
        elif state == STATE_RX_TRANSMISSION_INIT:
            state, rx_list_received_payload, rx_previous_cnt = run_st_rx_transmission_init()

        elif state == STATE_RX_TRANSMISSION_RECEIVE_MSG:
            state, rx_previous_cnt, rx_list_received_payload = \
                run_st_rx_transmission_receive_msg(rx_previous_cnt, rx_list_received_payload)

        elif state == STATE_RX_DECOMPRESS:
            state = run_st_rx_decompress(rx_list_received_payload)

        elif state == STATE_RX_MOUNT_USB:
            # stuck here until the USB is detected and mounted
            state = run_st_rx_mount_usb()

        elif state == STATE_RX_COPY_TO_USB:
            state = run_st_rx_copy_to_usb()

        # Network Mode states
        elif state == STATE_NM:
            state = run_st_network_mode()


if __name__ == "__main__":
    main()
