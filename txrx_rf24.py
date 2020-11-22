#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
# import os
from RF24 import *
import RPi.GPIO as GPIO
# import math
import zlib

# ----------- Pin set-up ----------- #

# Set the CE and CSN pins
RADIO = RF24(22, 0)

# Set the IRQ pin. Disconnected by the moment (GPIO24)
IRQ_GPIO_PIN = None
# IRQ_GPIO_PIN = 24

# ----------- Constants definitions ----------- #

PIPES = [0xF0F0F0F0E1, 0xF0F0F0F0D2]

# Role selection (0 --> receiver / 1 --> sender)
ROLE = 0

# States definition
E_INI_STATE = 0
E_SENDER_SEND_STATE = 1
E_SENDER_RECEIVE_STATE = 2
E_RECEIVER_STATE = 3


# ----------- Functions definition ----------- #

def ini_state_function():
    RADIO.begin()
    RADIO.enableDynamicPayloads()  # Dynamic ACK enables
    RADIO.setRetries(5, 15)  # RADIO.setchannel()

    if ROLE == 0:  # Receiver
        if IRQ_GPIO_PIN is not None:
            # set up callback for irq pin
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(IRQ_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(IRQ_GPIO_PIN, GPIO.FALLING, callback=try_read_data)  # TODO
        RADIO.openWritingPipe(PIPES[1])
        RADIO.openReadingPipe(1, PIPES[0])
        RADIO.startListening()
        r_state = E_RECEIVER_STATE

    else:  # Sender
        RADIO.openWritingPipe(PIPES[0])
        RADIO.openReadingPipe(1, PIPES[1])
        r_state = E_SENDER_SEND_STATE
    return r_state


def sender_send_function(p_file_content, pr_still_messages_to_send):
    RADIO.stopListening()
    # content_to_send = b""
    print(len(p_file_content))
    if len(p_file_content) > 1:
        content_to_send = p_file_content
    else:
        # EOF
        content_to_send = b"0"
        pr_still_messages_to_send = 0
    RADIO.write(content_to_send[0:31])
    # text_to_send = bytes()
    r_state = E_SENDER_RECEIVE_STATE
    return r_state, pr_still_messages_to_send


def sender_receive_function(pr_file_content, p_still_messages_to_send):
    RADIO.startListening()

    # Wait here until we get a response, or timeout
    started_waiting_at = millis()
    timeout = False
    while (not RADIO.available()) and (not timeout):
        if (millis() - started_waiting_at) > 500:
            timeout = True

    if timeout:
        print("failed, response timed out.")
    else:  # Message received
        lent = RADIO.getDynamicPayloadSize()
        receive_payload = RADIO.read(lent)
        # response_received = bytes(receive_payload)
        # Check if it is the last message
        if len(receive_payload) == 1:
            pass
            # Check if the character of the EOF is correct
            # communication_on = 0
            # Prepare next message to be send
        if p_still_messages_to_send == 1:
            pr_file_content = pr_file_content.replace(pr_file_content[0:31], b"")
    time.sleep(0.1)
    r_state = E_SENDER_SEND_STATE
    return r_state, pr_file_content


def receiver_function(pr_message_to_add_to_file, pr_communication_on, pr_compressed_file_received):
    if RADIO.available():
        lent = RADIO.getDynamicPayloadSize()
        receive_payload = RADIO.read(lent)
        if len(receive_payload) == 1:  # Last message
            print("Last message")
            pr_compressed_file_received += pr_message_to_add_to_file
            print(len(pr_compressed_file_received))
            decompressed_bytes = zlib.decompress(pr_compressed_file_received, wbits=15)
            with open("textfile_r.txt", "wb") as text_file:
                text_file.write(decompressed_bytes)
            pr_communication_on = 0
        else:  # Message expected
            if pr_message_to_add_to_file != receive_payload:
                pr_compressed_file_received += pr_message_to_add_to_file
            pr_message_to_add_to_file = receive_payload

        RADIO.stopListening()
        # Send the ACK (in this case the same message)(future implementation)
        RADIO.write(receive_payload)
        RADIO.startListening()
        return pr_message_to_add_to_file, pr_communication_on, pr_compressed_file_received


def millis():
    return int(round(time.time() * 1000))


def main():
    # Variables
    state = E_INI_STATE
    communication_on = 1  # ON --> 1 / 0 --> OFF
    # message_numeration = 1  # Messages numeration --> 1-9 / 0 last message
    # message_numeration_receiver = 1
    message_to_add_to_file = b""  # Message to write into text file
    # last_character_position = 0
    still_messages_to_send = 1
    compressed_file_received = b""

    # ----------- Read & write file text ----------- #

    # Read text file and transform it into bytes
    with open("textfile.txt", "rb") as f:
        file = f.read()
    file_content = zlib.compress(file, level=9)

    # Open the text file were the data will be printed into
    with open("textfile_r.txt", "wb") as text_file:
        text_file.write(b"")

    # ----------- Start communication ----------- #

    # Time start
    print("Start")

    while communication_on == 1:
        if state == E_INI_STATE:
            state = ini_state_function()
        elif state == E_SENDER_SEND_STATE:
            state, still_messages_to_send = sender_send_function(file_content, still_messages_to_send)
        elif state == E_SENDER_RECEIVE_STATE:
            state, file_content = sender_receive_function(file_content, still_messages_to_send)
        elif state == E_RECEIVER_STATE:
            message_to_add_to_file, communication_on, compressed_file_received = \
                receiver_function(message_to_add_to_file, communication_on, compressed_file_received)
        else:
            print("Error: No state selected")

    RADIO.stopListening()
    print("Finish")


if __name__ == "__main__":
    main()
