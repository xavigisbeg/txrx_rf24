#!/usr/bin/env python

import time
import os
from RF24 import *
import RPi.GPIO as GPIO
import math
import zlib

''' Functions definition '''


def ini_state_function(l_role):

    radio.begin()
    radio.enableDynamicPayloads()  # Dynamic ACK enables
    radio.setRetries(5, 15)  # radio.setchannel()

    if l_role == 0:  # Receiver
        if irq_gpio_pin is not None:
            # set up callback for irq pin
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(irq_gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(irq_gpio_pin, GPIO.FALLING, callback=try_read_data)  # TODO
        radio.openWritingPipe(pipes[1])
        radio.openReadingPipe(1, pipes[0])
        radio.startListening()
        l_state = RECEIVER_STATE

    else:  # Sender
        radio.openWritingPipe(pipes[0])
        radio.openReadingPipe(1, pipes[1])
        l_state = SENDER_SEND_STATE
    return l_state


def sender_send_function():
    global state
    global still_messages_to_send
    global message_numeration
    global file_content
    global last_character_position

    radio.stopListening()
    content_to_send = b""
    print(len(file_content))
    if len(file_content) > 1:
        content_to_send = file_content
    else:
        # EOF
        content_to_send = b"0"
        still_messages_to_send = 0
    radio.write(content_to_send[0:31])
    text_to_send = bytes()
    state = SENDER_RECEIVE_STATE


def sender_receive_function():
    global state
    global still_messages_to_send
    global message_numeration
    global communication_on
    global file_content
    global last_character_position

    radio.startListening()

    # Wait here until we get a response, or timeout
    started_waiting_at = millis()
    timeout = False
    while (not radio.available()) and (not timeout):
        if (millis() - started_waiting_at) > 500:
            timeout = True

    if timeout:
        print('failed, response timed out.')
    else:  # Message received
        lent = radio.getDynamicPayloadSize()
        receive_payload = radio.read(lent)
        response_received = bytes(receive_payload)
        # Check if it is the last message
        if len(receive_payload) == 1:
            pass
            # Check if the character of the EOF is correct
            # communication_on = 0
            # Prepare next message to be send
        if still_messages_to_send == 1:
            file_content = file_content.replace(file_content[0:31], b"")
    time.sleep(0.1)
    state = SENDER_SEND_STATE


def receiver_function():
    global state
    global message_numeration_receiver
    global message_to_add_to_file
    global communication_on
    global compressed_file_received

    if radio.available():
        lent = radio.getDynamicPayloadSize()
        receive_payload = radio.read(lent)
        if len(receive_payload) == 1:  # Last message
            print("Last message")
            compressed_file_received += message_to_add_to_file
            print(len(compressed_file_received))
            decompressed_bytes = zlib.decompress(compressed_file_received, wbits=15)
            with open('textfile_r.txt', "wb") as text_file:
                text_file.write(decompressed_bytes)
            communication_on = 0
        else:  # Message expected
            if message_to_add_to_file != receive_payload:
                compressed_file_received += message_to_add_to_file
            message_to_add_to_file = receive_payload

        radio.stopListening()
        # Send the ACK (in this case the same message)(future implementation)
        radio.write(receive_payload)
        radio.startListening()


''' Pin set-up '''

# Set the CE and CSN pins
radio = RF24(22, 0)

# Set the IRQ pin. Disconnected by the moment (GPIO24)
irq_gpio_pin = None
# irq_gpio_pin = 24

''' Constants definitions '''

pipes = [0xF0F0F0F0E1, 0xF0F0F0F0D2]

# Role selection (0 --> receiver / 1 --> sender)
role = 0

# States definition
INI_STATE = 0
SENDER_SEND_STATE = 1
SENDER_RECEIVE_STATE = 2
RECEIVER_STATE = 3
state = INI_STATE

# Variables
communication_on = 1  # ON --> 1 / 0 --> OFF
message_numeration = 1  # Messages numeration --> 1-9 / 0 last message
message_numeration_receiver = 1
message_to_add_to_file = b""  # Message to write into text file
last_character_position = 0
still_messages_to_send = 1
compressed_file_received = b""

''' Read & write file text '''

# Read text file and transform it into bytes
with open('textfile.txt', "rb") as f:
    file = f.read()
file_content = zlib.compress(file, level=9)


# Open the text file were the data will be printed into
with open('textfile_r.txt', "wb") as text_file:
    text_file.write(b"")

''' Start comunnication '''

# Time start
millis = lambda: int(round(time.time() * 1000))

print('Start')

while communication_on == 1:
    if state == INI_STATE:
        state = ini_state_function(role)
    elif state == SENDER_SEND_STATE:
        sender_send_function()
    elif state == SENDER_RECEIVE_STATE:
        sender_receive_function()
    elif state == RECEIVER_STATE:
        receiver_function()
    else:
        print("Error: No state selected")

radio.stopListening()
print('Finish')
