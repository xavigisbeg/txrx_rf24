# -*- coding: utf-8 -*-

from txrx_functions import *


# ------------ Main Function ------------ #

def main():
    # Initialization of variables
    state = STATE_INIT

    tx_list_of_frames = [bytearray(b"")]
    tx_frame_num = 0

    rx_previous_cnt = -1
    rx_list_received_payload = list()

    while True:
        # At any time we should return to the init state if the start switch is turned off
        if state != STATE_INIT:
            state = run_st_read_start_switch(state)

        # At any time in transmission in TX, if the enable transmission switch is turned off
        # we go back to the waiting for enabling transmission state
        if state in [STATE_TX_TRANSMISSION_INIT, STATE_TX_TRANSMISSION_SEND_MSG, STATE_TX_TRANSMISSION_SEND_EOT]:
            state = run_st_tx_read_transmission_enable_switch(state)

        # At any time in transmission in RX, if the enable transmission switch is turned off
        # if the file was received successfully, we go to the USB mount state
        # else, we go back to the waiting for enabling transmission state
        if state in [STATE_RX_TRANSMISSION_INIT, STATE_RX_TRANSMISSION_RECEIVE_MSG,
                     STATE_RX_TRANSMISSION_SEND_NOK_ACK, STATE_RX_TRANSMISSION_SEND_OK_ACK]:
            state = run_st_rx_read_transmission_enable_switch(state)

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
            state, tx_list_of_frames = run_st_tx_create_frames()
            # print(f"Number of messages: {len(tx_list_of_frames)}")

        elif state == STATE_TX_WAIT_FOR_TRANSMISSION_ENABLE:
            # stuck here until the enable transmission switch is ON
            state = run_st_tx_read_transmission_enable_switch(state)

        elif state == STATE_TX_TRANSMISSION_INIT:
            state, tx_frame_num = run_st_tx_transmission_init()

        elif state == STATE_TX_TRANSMISSION_SEND_MSG:
            state, tx_frame_num = run_st_tx_transmission_send_msg(tx_list_of_frames, tx_frame_num)

        elif state == STATE_TX_TRANSMISSION_SEND_EOT:
            state = run_st_tx_transmission_send_eot()

        # Receiver states
        elif state == STATE_RX_WAIT_FOR_TRANSMISSION_ENABLE:
            # stuck here until the enable transmission switch is ON
            state = run_st_rx_read_transmission_enable_switch(state)

        elif state == STATE_RX_TRANSMISSION_INIT:
            state, rx_list_received_payload, rx_previous_cnt = run_st_rx_transmission_init()

        elif state == STATE_RX_TRANSMISSION_RECEIVE_MSG:
            state, rx_previous_cnt, rx_list_received_payload = \
                run_st_rx_transmission_receive_msg(rx_previous_cnt, rx_list_received_payload)

        elif state == STATE_RX_DECOMPRESS:
            state = run_st_rx_decompress(rx_list_received_payload)

        elif state == STATE_RX_TRANSMISSION_SEND_NOK_ACK:
            state, rx_list_received_payload, rx_previous_cnt = run_st_rx_transmission_send_nok_ack()

        elif state == STATE_RX_TRANSMISSION_SEND_OK_ACK:
            state = run_st_rx_transmission_send_ok_ack()

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
