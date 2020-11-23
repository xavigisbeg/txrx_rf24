# -*- coding: utf-8 -*-

from txrx_utils import *
from txrx_functions import *
import time
import os
from RF24 import *
import RPi.GPIO as GPIO



# ------------ Main Function ------------ #

def main():
    ''' Pin set-up '''

    # Set the CE and CSN pins
    radio = RF24(22, 0)

    # Set the IRQ pin. Disconnected by the moment (GPIO24)
    irq_gpio_pin = None
    # irq_gpio_pin = 24

    ''' Constants definitions '''

    pipes = [0xF0F0F0F0E1, 0xF0F0F0F0D2]

    # Initialization of variables
    state = STATE_INIT
    tx_list_of_frames = [bytearray(b"")]
    tx_frame_num = 0
    rx_message_to_add_to_file = b""

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
            state, tx_list_of_frames = run_st_tx_create_frames()

        elif state == STATE_TX_TRANSMISSION_INIT:
            state, tx_frame_num = run_st_tx_transmission_init(radio, pipes)

        elif state == STATE_TX_TRANSMISSION_SEND_MSG:
            state = run_st_tx_transmission_send_msg(radio, tx_list_of_frames, tx_frame_num)

        elif state == STATE_TX_TRANSMISSION_RECEIVE_ACK:
            state, tx_frame_num = run_st_tx_transmission_receive_ack(tx_list_of_frames, tx_frame_num)

        elif state == STATE_TX_TRANSMISSION_SEND_EOT:
            state = run_st_tx_transmission_send_eot(radio)

        elif state == STATE_TX_TRANSMISSION_RECEIVE_EOT_ACK:
            state = run_st_tx_transmission_receive_eot_ack()

        # Receiver states
        elif state == STATE_RX_TRANSMISSION_INIT:
            state, rx_message_to_add_to_file = run_st_rx_transmission_init(radio, pipes, irq_gpio_pin, GPIO)

        elif state == STATE_RX_TRANSMISSION_RECEIVE_MSG:
            state, rx_message_to_add_to_file = run_st_rx_transmission_receive_msg(radio, rx_message_to_add_to_file)

        elif state == STATE_RX_DECOMPRESS:
            state = run_st_rx_decompress()

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
