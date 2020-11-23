import time
import os
import math
import zlib
from RF24 import *
from txrx_utils import *


LENGTH_OF_FRAMES = 32
NAME_OF_FILE = "text_file.txt"
END_OF_TRANSMISSION = bytearray(b"The transmission is over now!!!")


# ------------ Common functions ------------ #

def run_st_read_start_switch(pr_state):
    """ Read the start switch """
    start_switch = True  # TODO function to read the start switch
    # could be nice to have a function that returns every GPIOs
    if pr_state == STATE_INIT:
        if start_switch:  # if the start switch is ON
            pr_state = STATE_READ_SWITCHES  # we start the process
    else:
        if not start_switch:  # if at anytime the start switch is OFF
            pr_state = STATE_INIT  # we return to the init state
    return pr_state


def run_st_read_switches():
    """ Read the switches for the Network Mode and the TX/RX """
    network_mode_switch = False  # TODO function to read the Network Mode switch
    tx_switch = False  # TODO function to read the TX/RX switch
    if network_mode_switch:
        r_state = STATE_NM
    else:  # Individual Modes
        if tx_switch:  # transmitter
            r_state = STATE_TX_MOUNT_USB
        else:  # receiver
            r_state = STATE_RX_TRANSMISSION_INIT
    return r_state


# ------------ Transmitter functions ------------ #

def run_st_tx_mount_usb():
    """ Try to mount the USB """
    usb_mounted = True  # TODO function to try to mount the USB and return True if the USB is mounted, False else
    if usb_mounted:  # if the usb is mounted, we go to the state copy from usb
        r_state = STATE_TX_COPY_FROM_USB
    else:  # else, we remain in the same state
        r_state = STATE_TX_MOUNT_USB
    return r_state


def run_st_tx_copy_from_usb():
    """ Copy the .txt file from the usb to the working directory under the name NAME_OF_FILE """
    # TODO copy the .txt file from the usb to the working directory under the name NAME_OF_FILE
    r_state = STATE_TX_COMPRESS
    return r_state


def run_st_tx_compress():
    """ Open the .txt file in the working directory under the name NAME_OF_FILE and compress it """
    with open(NAME_OF_FILE, "rb") as f:
        text_bytes = f.read()
    compressed_bytes = zlib.compress(text_bytes, level=9)
    # We save the compressed bytes inside a new file
    with open("compressed_" + NAME_OF_FILE, "wb") as f:
        f.write(compressed_bytes)
    r_state = STATE_TX_CREATE_FRAMES_TO_SEND
    return r_state


def run_st_tx_create_frames():
    """ Create a list of bytearray to be sent, each of length LENGTH_OF_FRAMES """
    with open("compressed_" + NAME_OF_FILE, "rb") as f:
        compressed_bytes = f.read()
    r_list_of_frames = list()
    while len(compressed_bytes) > 0:  # while there are still bytes to add to the list
        current_bytes = compressed_bytes[:LENGTH_OF_FRAMES]  # we take the first bytes up to the length
        r_list_of_frames.append(bytearray(current_bytes))
        compressed_bytes = compressed_bytes[LENGTH_OF_FRAMES:]  # we remove the bytes put in the list
    r_state = STATE_TX_TRANSMISSION_INIT
    return r_state, r_list_of_frames


def run_st_tx_transmission_init():
    """ Initialize the transmitter and the object radio """
    # TODO
    # The objects radio, irq_gpio_pin, pipes will be global in this file
    r_frame_num = 0  # we start to send the first message
    r_state = STATE_TX_TRANSMISSION_SEND_MSG
    return r_state, r_frame_num


def run_st_tx_transmission_send_msg(p_list_of_frames, p_frame_num):
    """ Send one frame from the list of frames """
    # TODO
    frame_to_send = p_list_of_frames[p_frame_num]
    r_state = STATE_TX_TRANSMISSION_RECEIVE_ACK
    return r_state


def run_st_tx_transmission_receive_ack(p_list_of_frames, p_frame_num):
    """ Wait for the acknowledgement from the receiver """
    # TODO check if the received frame corresponds to the reference frame
    ref_frame = p_list_of_frames[p_frame_num]
    ack = True  # TODO if there is an error, the ack should be False
    if ack:  # if we have received the acknowledgement, we can send the next message
        p_frame_num += 1
    if p_frame_num < len(p_list_of_frames):  # still frames to be sent
        r_state = STATE_TX_TRANSMISSION_SEND_MSG
    else:  # no more frame to be sent
        r_state = STATE_TX_TRANSMISSION_SEND_EOT  # we have to send the end of transmission
    return r_state, p_frame_num


def run_st_tx_transmission_send_eot():
    """ Send the end of transmission """
    # TODO
    frame_to_send = END_OF_TRANSMISSION
    r_state = STATE_TX_TRANSMISSION_RECEIVE_EOT_ACK
    return r_state


def run_st_tx_transmission_receive_eot_ack():
    """ Wait for the acknowledgement of the EOT from the receiver """
    # TODO check if the received frame corresponds to the reference frame
    ref_frame = END_OF_TRANSMISSION
    ack = True  # TODO if there is an error, the ack should be False
    if ack:  # if we have received the acknowledgement of the EOT, we are done
        r_state = STATE_FINAL
    else:  # else, we should retry to send the EOT
        r_state = STATE_TX_TRANSMISSION_SEND_EOT
    return r_state


# ------------ Receiver functions ------------ #

def run_st_rx_transmission_init():
    """ Initialize the receiver and the object radio """
    # TODO
    # The objects radio, irq_gpio_pin, pipes will be global in this file
    r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
    return r_state


def run_st_rx_transmission_receive_msg(pr_message_to_add_to_file):
    """ Wait for a message and send back an acknowledgment when received """
    # TODO Check if the received payload corresponds or not to the EOT
    # When we receive a frame, we should send the acknowledgement
    # The frames we receive are appended to a file ("compressed_" + NAME_OF_FILE)
    received_payload = b""
    if received_payload == END_OF_TRANSMISSION:
        with open("compressed_" + NAME_OF_FILE, "ab") as f:
            f.write(pr_message_to_add_to_file)
        r_state = STATE_RX_DECOMPRESS
    else:
        if pr_message_to_add_to_file != received_payload:
            with open("compressed_" + NAME_OF_FILE, "ab") as f:
                f.write(pr_message_to_add_to_file)
        pr_message_to_add_to_file = received_payload
        r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
    # Send ACK
    return r_state, pr_message_to_add_to_file


def run_st_rx_decompress():
    """ Decompress the received frames """
    with open("compressed_" + NAME_OF_FILE, "rb") as f:
        compressed_bytes = f.read()
    decompressed_bytes = zlib.decompress(compressed_bytes, wbits=15)
    with open(NAME_OF_FILE, "wb") as f:
        f.write(decompressed_bytes)
    r_state = STATE_RX_MOUNT_USB
    return r_state


def run_st_rx_mount_usb():
    """ Try to mount the USB """
    usb_mounted = True  # TODO function to try to mount the USB and return True if the USB is mounted, False else
    if usb_mounted:  # if the usb is mounted, we go to the state copy from usb
        r_state = STATE_RX_COPY_TO_USB
    else:  # else, we remain in the same state
        r_state = STATE_RX_MOUNT_USB
    return r_state


def run_st_rx_copy_to_usb():
    """ Copy the .txt file from the working directory to the usb """
    # TODO copy the .txt file from the working directory to the usb
    r_state = STATE_FINAL
    return r_state


# ------------ Network Mode functions ------------ #

def run_st_network_mode():  # TODO
    """ Network Mode """
    r_state = STATE_FINAL
    return r_state
