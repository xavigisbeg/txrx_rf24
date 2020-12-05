# -*- coding: utf-8 -*-

import time
import zlib

import RPi.GPIO as GPIO
from RF24 import *

from txrx_utils import *
from NM_GENERAL import nm_initialisation_nrf24, nm_network_mode


# ----------- Constants Definition ----------- #
LENGTH_OF_FRAMES = 31  # one byte is needed for the header
NAME_OF_INPUT_FILE = ["MTP-F20-", "-B-TX.txt"]
NAME_OF_OUTPUT_FILE = ["MTP-F20-", "-B-RX.txt"]
END_OF_TRANSMISSION = create_header(0, eot=True)
OK_MESSAGE = bytearray(b"OK")
NOK_MESSAGE = bytearray(b"NOK")

# ----------- Radio set-up ----------- #
# RADIO = RF24(22, 0, 1_000_000)  # 22: CE GPIO, 0: CSN GPIO, SPI speed: 1 MHz
# RADIO = RF24(22, 0, 5_000_000)  # 22: CE GPIO, 0: CSN GPIO, SPI speed: 5 MHz
RADIO = RF24(22, 0)  # 22: CE GPIO, 0: CSN GPIO, (SPI speed: 10 MHz)
PIPES = [0xBB_BB_BB_BB_B0, 0xBB_BB_BB_BB_B1]  # address of the pipes

# Set the IRQ pin. Disconnected by the moment (GPIO24)
IRQ_GPIO_PIN = None
# IRQ_GPIO_PIN = 24


# ------------ Common state functions ------------ #

def run_st_read_start_switch(pr_state):
    """ Read the start switch """
    start_switch = I_FACE.sw.start.is_on()
    if pr_state == STATE_INIT:
        if start_switch:  # if the start switch is ON
            print("Start process")
            I_FACE.led.start.on()  # LED to indicate the process has started
            pr_state = STATE_READ_SWITCHES  # we start the process
    else:
        if not start_switch:  # if at anytime the start switch is OFF
            I_FACE.led.all_off()  # switch off every LED
            RADIO.stopListening()
            pr_state = STATE_INIT  # we return to the init state
    return pr_state


def run_st_read_switches():
    """ Read the switches for the Network Mode and the TX/RX """
    I_FACE.sw.update_switches()  # we update all the switches
    mode = I_FACE.get_mode()
    if mode:  # a mode was selected
        print(f"Mode selected: {mode}")
        if mode == "NM":
            r_state = STATE_NM
        else:  # Individual Modes, SRI or MRM
            tx_switch = I_FACE.sw.Tx.was_on()
            print("Transmitter" if tx_switch else "Receiver" + " selected")
            if tx_switch:  # transmitter
                r_state = STATE_TX_MOUNT_USB
            else:  # receiver
                r_state = STATE_RX_WAIT_FOR_TRANSMISSION_ENABLE
    else:  # no proper mode was selected, we read the switches again
        print("No proper mode selected")
        r_state = STATE_READ_SWITCHES
    return r_state


# ------------ Transmitter state functions ------------ #

def run_st_tx_mount_usb():
    """ Try to mount the USB """
    usb_mounted = mount_usb()
    if usb_mounted:  # if the usb is mounted, we go to the state copy from usb
        I_FACE.led.mounted.on()  # LED to tell that the USB is correctly mounted
        time.sleep(1)
        r_state = STATE_TX_COPY_FROM_USB
    else:  # else, we remain in the same state
        r_state = STATE_TX_MOUNT_USB
    return r_state


def run_st_tx_copy_from_usb():
    """ Copy the .txt file from the usb to the working directory under the name NAME_OF_FILE """
    mode = I_FACE.get_mode()
    input_file = mode.join(NAME_OF_INPUT_FILE)

    file = get_proper_txt_file(input_file, mode)

    if file:
        print("The USB contains the .txt file: " + file)
        cmd = "sudo cp " + os.path.join(USB_FOLDER, file) + " " + input_file
        print("\t > " + cmd)
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.SubprocessError:  # an error occurs during the copying
            I_FACE.led.mounted.off()
            unmount_usb()
            r_state = STATE_TX_MOUNT_USB  # try to remount the USB
            return r_state
        unmount_usb()
        r_state = STATE_TX_COMPRESS
    else:
        print("The USB does not contain any .txt file")
        I_FACE.led.mounted.off()
        unmount_usb()
        r_state = STATE_TX_MOUNT_USB  # try to remount the USB
    return r_state


def run_st_tx_compress():
    """ Open the .txt file in the working directory under the name NAME_OF_FILE and compress it """
    mode = I_FACE.get_mode()
    input_file = mode.join(NAME_OF_INPUT_FILE)

    with open(input_file, "rb") as f:
        text_bytes = f.read()

    compressed_bytes = zlib.compress(text_bytes, level=9)

    # We save the compressed bytes inside a new file
    with open("compressed_" + input_file, "wb") as f:
        f.write(compressed_bytes)

    r_state = STATE_TX_CREATE_FRAMES_TO_SEND
    return r_state


def run_st_tx_create_frames():
    """ Create a list of bytearray to be sent, each of length LENGTH_OF_FRAMES """
    mode = I_FACE.get_mode()
    input_file = mode.join(NAME_OF_INPUT_FILE)

    with open("compressed_" + input_file, "rb") as f:
        compressed_bytes = f.read()

    r_list_of_frames = list()
    frame_num = 0
    while len(compressed_bytes) > 0:  # while there are still bytes to add to the list
        current_bytes = compressed_bytes[:LENGTH_OF_FRAMES]  # we take the first bytes up to the length
        header = create_header(frame_num)
        r_list_of_frames.append(bytearray(header + current_bytes))

        compressed_bytes = compressed_bytes[LENGTH_OF_FRAMES:]  # we remove the bytes put in the list
        frame_num += 1

    I_FACE.led.ready.on()  # LED to tell that the transmitter is ready to send
    r_state = STATE_TX_WAIT_FOR_TRANSMISSION_ENABLE
    return r_state, r_list_of_frames


def run_st_tx_read_transmission_enable_switch(pr_state):
    """ Read the enable transmission switch in TX mode """
    en_transmission_switch = I_FACE.sw.en_transmission.is_on()
    if pr_state == STATE_TX_WAIT_FOR_TRANSMISSION_ENABLE:
        if en_transmission_switch:  # if the en_transmission switch is ON
            pr_state = STATE_TX_TRANSMISSION_INIT  # we start the transmission
    else:
        if not en_transmission_switch:  # if at anytime in transmission the en_transmission switch is OFF
            I_FACE.led.transmission.off()  # LED for the transmission: the transmission is over, it's OFF
            pr_state = STATE_TX_WAIT_FOR_TRANSMISSION_ENABLE  # we return to the waiting state for transmission
    return pr_state


def common_transceiver_init():
    """ Initialize the common parameters for both the transmitter and the receiver """
    RADIO.begin()

    RADIO.setPALevel(RF24_PA_HIGH)  # RF24_PA_MIN, RF24_PA_LOW, RF24_PA_HIGH and RF24_PA_MAX
    RADIO.setDataRate(RF24_1MBPS)  # RF24_250KBPS for 250kbs, RF24_1MBPS for 1Mbps, or RF24_2MBPS for 2Mbps
    RADIO.setRetries(1, 15)  # 1 -> delay from 0 up to 15 [(delay+1)*250 µs] (1-> 500µs),
    #                         15 -> retries number from 0 (no retries) up to 15
    RADIO.setAutoAck(True)  # Enable auto-acknowledgement
    RADIO.enableAckPayload()  # Enable acknowledgement payload
    RADIO.enableDynamicPayloads()  # Enable dynamic-sized payloads
    RADIO.setChannel(1)  # RF channel to communicate on: 0-125
    RADIO.setCRCLength(RF24_CRC_16)  # RF24_CRC_8 for 8-bit or RF24_CRC_16 for 16-bit


def run_st_tx_transmission_init():
    """ Initialize the transmitter and the object radio """
    common_transceiver_init()

    RADIO.openWritingPipe(PIPES[0])
    RADIO.openReadingPipe(1, PIPES[1])
    RADIO.stopListening()

    I_FACE.led.reboot.off()  # reboot LED turned off, if it was ON
    r_frame_num = 0  # we start to send the first message
    r_state = STATE_TX_TRANSMISSION_SEND_MSG
    return r_state, r_frame_num


def run_st_tx_transmission_send_msg(p_list_of_frames, pr_frame_num):
    """ Send one frame from the list of frames """
    frame_to_send = p_list_of_frames[pr_frame_num]

    if RADIO.write(frame_to_send):  # the frame was correctly sent
        if pr_frame_num % 50 == 0:  # LED for the transmission:
            # at the start of the transmission, it is ON
            # and then every 50 frames, it changes its state
            I_FACE.led.transmission.toggle()
        pr_frame_num += 1
        if pr_frame_num < len(p_list_of_frames):  # still frames to send
            r_state = STATE_TX_TRANSMISSION_SEND_MSG
        else:  # no more frame to send
            while RADIO.available():  # to flush the FIFO of ACK
                received_msg_length = RADIO.getDynamicPayloadSize()
                RADIO.read(received_msg_length)
            r_state = STATE_TX_TRANSMISSION_SEND_EOT  # we have to send the end of transmission
    else:
        print(f"Max number of retries reached {pr_frame_num}: {frame_to_send}")
        r_state = STATE_TX_TRANSMISSION_SEND_MSG
    return r_state, pr_frame_num


def run_st_tx_transmission_send_eot():
    """ Send the end of transmission """
    frame_to_send = END_OF_TRANSMISSION
    if RADIO.write(frame_to_send):  # the EOT was correctly sent
        r_state = STATE_TX_TRANSMISSION_SEND_EOT
        if not RADIO.available():
            print("Received empty ACK for the EOT")
        else:
            received_msg_length = RADIO.getDynamicPayloadSize()
            bytearray_payload = RADIO.read(received_msg_length)
            if bytearray_payload == NOK_MESSAGE:  # Reset transmission
                print("Received NOK for the EOT, RESET TRANSMISSION")
                I_FACE.led.reboot.on()  # LED to tell the system is rebooting
                I_FACE.led.ready.off()
                I_FACE.led.transmission.off()  # LED for the transmission: the transmission is over, it's OFF
                r_state = STATE_TX_COMPRESS  # We return to the compression state
            elif bytearray_payload == OK_MESSAGE:  # End transmission
                print("Received OK for the EOT, END TRANSMISSION")
                I_FACE.led.transmission.off()  # LED for the transmission: the transmission is over, it's OFF
                I_FACE.led.success.on()
                r_state = STATE_FINAL
    else:
        print("Max number of retries reached: EOT")
        r_state = STATE_TX_TRANSMISSION_SEND_EOT

    return r_state


# ------------ Receiver state functions ------------ #

def run_st_rx_read_transmission_enable_switch(pr_state):
    """ Read the enable transmission switch in RX mode """
    mode = I_FACE.get_mode()
    output_file = mode.join(NAME_OF_OUTPUT_FILE)

    en_transmission_switch = I_FACE.sw.en_transmission.is_on()
    if pr_state == STATE_RX_WAIT_FOR_TRANSMISSION_ENABLE:
        if en_transmission_switch:  # if the en_transmission switch is ON
            print("Init transmission")
            pr_state = STATE_RX_TRANSMISSION_INIT  # we start the transmission
    else:
        if not en_transmission_switch:  # if at anytime in transmission the en_transmission switch is OFF
            print("Disabling transmission")
            RADIO.stopListening()
            I_FACE.led.transmission.off()  # LED for the transmission: the transmission is over, it's OFF
            if os.path.exists(output_file):
                pr_state = STATE_RX_MOUNT_USB  # we go to the USB mount state
            else:
                pr_state = STATE_RX_WAIT_FOR_TRANSMISSION_ENABLE  # we return to the waiting state for transmission
    return pr_state


def run_st_rx_transmission_init():
    """ Initialize the receiver and the object radio """
    common_transceiver_init()

    if IRQ_GPIO_PIN is not None:
        # set up callback for irq pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IRQ_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(IRQ_GPIO_PIN, GPIO.FALLING, callback=try_read_data)

    RADIO.openWritingPipe(PIPES[1])
    RADIO.openReadingPipe(1, PIPES[0])
    RADIO.startListening()

    r_list_received_payload = list()
    r_previous_cnt = -1
    r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
    return r_state, r_list_received_payload, r_previous_cnt


def run_st_rx_transmission_receive_msg(pr_previous_cnt, pr_list_received_payload):
    """ Wait for a message """
    r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
    if RADIO.available():
        if len(pr_list_received_payload) % 50 == 0:  # LED for the transmission:
            # at the start of the transmission, it is ON
            # and then every 50 frames, it changes its state
            I_FACE.led.transmission.toggle()
        received_msg_length = RADIO.getDynamicPayloadSize()
        total_payload = bytes(RADIO.read(received_msg_length))
        received_payload, eot, cnt = split_received_msg(total_payload)

        if eot:
            print(f"Received EOT")
            I_FACE.led.transmission.off()
            RADIO.stopListening()
            r_state = STATE_RX_DECOMPRESS
        elif cnt != pr_previous_cnt:  # test if we haven't twice the same message
            pr_previous_cnt = cnt
            print(f"Received packet ({len(pr_list_received_payload)}) {received_payload}")
            pr_list_received_payload.append(received_payload)
    return r_state, pr_previous_cnt, pr_list_received_payload


def run_st_rx_decompress(p_list_received_payload):
    """ Decompress the received frames """
    mode = I_FACE.get_mode()
    output_file = mode.join(NAME_OF_OUTPUT_FILE)

    compressed_bytes = b"".join(p_list_received_payload)

    try:
        decompressed_bytes = zlib.decompress(compressed_bytes, wbits=15)
    except zlib.error:
        print("ERROR IN DECOMPRESSION")
        I_FACE.led.reboot.on()  # LED to tell the system is rebooting
        RADIO.startListening()
        RADIO.writeAckPayload(1, NOK_MESSAGE)  # send a NOK in the ACK payload to reset the transmission
        r_state = STATE_RX_TRANSMISSION_SEND_NOK_ACK  # an error in decompression, send an NOK to reset the transmission
        return r_state

    with open(output_file, "wb") as f:
        f.write(decompressed_bytes)

    I_FACE.led.ready.on()  # LED to tell that the receiver has correctly decompressed, it's ready to write to the USB
    r_state = STATE_RX_TRANSMISSION_SEND_OK_ACK
    RADIO.startListening()
    RADIO.writeAckPayload(1, OK_MESSAGE)  # send a OK in the ACK payload to validate the transmission
    return r_state


def run_st_rx_transmission_send_nok_ack():
    """ Send a NOK message to reset the transmission """
    r_state = STATE_RX_TRANSMISSION_SEND_NOK_ACK
    r_list_received_payload = list()
    r_previous_cnt = -1
    if RADIO.available():
        received_msg_length = RADIO.getDynamicPayloadSize()
        total_payload = bytes(RADIO.read(received_msg_length))
        received_payload, eot, cnt = split_received_msg(total_payload)

        if eot:
            print(f"Received EOT, we write a new NOK ack payload")
            RADIO.writeAckPayload(1, NOK_MESSAGE)
            r_state = STATE_RX_TRANSMISSION_SEND_NOK_ACK
        else:  # the transmitter has already starts the transmission of the file
            print("RESET TRANSMISSION")
            I_FACE.led.reboot.off()  # reboot LED turned off
            print(f"Received packet ({0}) {received_payload}")
            r_previous_cnt = cnt
            r_list_received_payload = [received_payload]
            r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG

    return r_state, r_list_received_payload, r_previous_cnt


def run_st_rx_transmission_send_ok_ack():
    """ Send a OK message to tell the transmitter that everything was fine """
    if RADIO.available():
        print(f"Received message, we write a new OK ack payload")
        received_msg_length = RADIO.getDynamicPayloadSize()
        RADIO.read(received_msg_length)
        RADIO.writeAckPayload(1, OK_MESSAGE)
    r_state = STATE_RX_TRANSMISSION_SEND_OK_ACK
    return r_state


def run_st_rx_mount_usb():
    """ Try to mount the USB """
    usb_mounted = mount_usb()
    if usb_mounted:  # if the usb is mounted, we go to the state copy from usb
        I_FACE.led.mounted.on()  # LED to tell that the USB is correctly mounted
        time.sleep(1)
        r_state = STATE_RX_COPY_TO_USB
    else:  # else, we remain in the same state
        r_state = STATE_RX_MOUNT_USB
    return r_state


def run_st_rx_copy_to_usb():
    """ Copy the .txt file from the working directory to the usb """
    mode = I_FACE.get_mode()
    output_file = mode.join(NAME_OF_OUTPUT_FILE)

    cmd = "sudo cp " + output_file + " " + USB_FOLDER
    print("\t > " + cmd)
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.SubprocessError:  # an error occurs during the copying
        I_FACE.led.mounted.off()
        unmount_usb()
        r_state = STATE_RX_MOUNT_USB  # try to remount the USB
        return r_state

    unmount_usb()
    I_FACE.led.success.on()
    r_state = STATE_FINAL
    return r_state


# ------------ Network Mode state functions ------------ #

def run_st_network_mode():
    """ Network Mode """
    nm_initialisation_nrf24()
    nm_network_mode()
    r_state = STATE_FINAL
    return r_state
