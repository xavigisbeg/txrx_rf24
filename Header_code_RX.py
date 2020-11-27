#!/usr/bin/env python

from __future__ import print_function
import time
import os
from RF24 import *
import RPi.GPIO as GPIO
import math
import zlib


##########  Functions definition  ##########

def ini_state_funtion(radio, p_role, p_pipes):

    radio.begin()
    radio.setAutoAck(True)  # Enable auto-acknowledgement
    radio.enableDynamicPayloads()  # Enable dynamic-sized payloads
    radio.setRetries(5, 15)  # radio.setchannel()
    radio.setChannel(1)  # RF channel to communicate on: 0-125
    radio.setCRCLength(RF24_CRC_16)  # RF24_CRC_8 for 8-bit or RF24_CRC_16 for 16-bit

    if p_role == 0:  # Receiver
        radio.openWritingPipe(p_pipes[1])
        radio.openReadingPipe(1, p_pipes[0])
        radio.startListening()
        p_state = RECEIVER_STATE
        return p_state

    else:  # Sender
        radio.openWritingPipe(p_pipes[0])
        radio.openReadingPipe(1, p_pipes[1])
        p_state = COMPRESS_STATE
        return p_state


def compress_file():
    with open('textfile.txt', "rb") as f:
        file = f.read()
    p_file_content_c = zlib.compress(file, level=9)
    p_state = SENDER_SEND_STATE
    return p_state, p_file_content_c

def decompress_and_createFile(p_file_compressed):
    decompressed_bytes = zlib.decompress(p_file_compressed, wbits=15)
    with open('textfile_r.txt', "wb") as text_file:
        text_file.write(decompressed_bytes)
    p_state = FINAL_STATE
    return p_state

def create_message(numeration, p_file_content_c):
    numeration_byte = bytearray(numeration.to_bytes(1, "big"))
    p_message =  numeration_byte + p_file_content_c[0:30]
    return p_message


def sender_send_function(p_file_content_c, message_numeration):
    radio.stopListening()
    print(len(p_file_content_c))
    if len(p_file_content_c) > 1:
        p_message = create_message(message_numeration, p_file_content_c)
        ACK = radio.write(p_message)
        if ACK == True:
            p_state = SENDER_RECEIVE_STATE
        else:
            p_state = SENDER_SEND_STATE
    else: #EOT
        p_state = SENDER_EOT_STATE

    return p_state


def sender_receive_function(p_file_content_compressed, p_numeration):

    # Prepare next message to be send
    p_file_content_compressed = p_file_content_compressed.replace(p_file_content_compressed[0:30], b"")
    p_numeration += 1
    if p_numeration == 10:
        p_numeration = 1

    time.sleep(0.1)
    state = SENDER_SEND_STATE

    return state, p_file_content_compressed, p_numeration


def sender_EOT(p_EOT_message, p_ACK_EOT_counter):
    ACK = radio.write(p_EOT_message)
    p_state = SENDER_EOT_STATE
    if ACK == True:
        print(p_ACK_EOT_counter)
        p_state = FINAL_STATE
    elif p_ACK_EOT_counter == 2000: # Aprox 30 seconds of trying retransmissions
        print("ERROR EOT")
        p_state = FINAL_STATE
    p_ACK_EOT_counter += 1
    return p_state, p_ACK_EOT_counter

def receiver_function(p_file_content_compressed, p_numeration, p_message_to_add, p_EOT_message):
    state = RECEIVER_STATE

    if radio.available():
        m = radio.getDynamicPayloadSize()
        received_message = radio.read(m)
        if received_message != p_EOT_message:
            if received_message[0] == p_numeration: # Correct expected
                if message_to_add != b"":
                    p_file_content_compressed += p_message_to_add
                p_numeration += 1
                if p_numeration == 10:
                    p_numeration = 1
            p_message_to_add = received_message[1:31]

        else: # EOT
            p_file_content_compressed += p_message_to_add
            print("EOT received")
            state = DECOMPRESS_STATE
    return state, p_file_content_compressed, p_numeration, p_message_to_add


def final():
    radio.stopListening()
    print('Finish')
    return 0


##########  Pin set-up  ##########

# Set the CE and CSN pins
radio = RF24(22, 0);

# Set the IRQ pin. Disconnected by the moment (GPIO24)
#irq_gpio_pin = None
# irq_gpio_pin = 24


##########  Constants definitions  ##########

pipes = [0xF0F0F0F0E1, 0xF0F0F0F0D2]

# Role selection (0 --> receiver / 1 --> sender)
role = 0

# States definition
INI_STATE = 0
COMPRESS_STATE = 1
SENDER_SEND_STATE = 2
SENDER_RECEIVE_STATE = 3
SENDER_EOT_STATE = 4
RECEIVER_STATE = 5
DECOMPRESS_STATE = 6
FINAL_STATE = 7

# Variables
communication_on = 1  # ON --> 1 / 0 --> OFF
s_message_numeration = 1  # Messages numeration --> 1-9 / 0 last message
r_message_numeration = 1
eot = 0
s_file_content_compressed = b""
r_file_content_compressed = b""
message_to_add = b""
EOT_message = b"File transmission finish! EOT"
ACK_EOT_counter = 0


##########  Start comunnication  ##########

# Time start
millis = lambda: int(round(time.time() * 1000))

print('Start')

state = INI_STATE

while communication_on == 1:
    if state == INI_STATE:
        state = ini_state_funtion(radio, role, pipes)
    elif state == COMPRESS_STATE:
        state, s_file_content_compressed = compress_file()
    elif state == SENDER_SEND_STATE:
        state = sender_send_function(s_file_content_compressed, s_message_numeration)
    elif state == SENDER_RECEIVE_STATE:
        state, s_file_content_compressed, s_message_numeration = sender_receive_function(s_file_content_compressed, s_message_numeration)
    elif state == SENDER_EOT_STATE:
        state, ACK_EOT_counter = sender_EOT(EOT_message, ACK_EOT_counter)
    elif state == RECEIVER_STATE:
        state, r_file_content_compressed, r_message_numeration, message_to_add = receiver_function(r_file_content_compressed, r_message_numeration, message_to_add, EOT_message)
    elif state == DECOMPRESS_STATE:
        state = decompress_and_createFile(r_file_content_compressed)
    elif state == FINAL_STATE:
        communication_on = final()
    else:
        print("Error: No state selected")
