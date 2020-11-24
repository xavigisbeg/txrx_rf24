import time
import os
import math
import subprocess
import zlib
from RF24 import *
from txrx_utils import *


# ----------- Global parameters ----------- #
LENGTH_OF_FRAMES = 32
USB_FOLDER = "/media/usb0"
NAME_OF_FILE = "text_file.txt"
END_OF_TRANSMISSION = bytearray(b"The transmission is over now!!!")
# END_OF_TRANSMISSION = bytearray(b"")

# ----------- Radio set-up ----------- #
RADIO = RF24(22, 0)  # 22: CE GPIO, 0: CSN GPIO, (SPI speed: 10 MHz)
PIPES = [0xF0F0F0F0E1, 0xF0F0F0F0D2]  # address of the pipes
# Set the IRQ pin. DIsconnected by the moment (GPIO24)
IRQ_GPIO_PIN = None
# IRQ_GPIO_PIN = 24


# ------------ Common state functions ------------ #

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
    create_mnt_usb_repo()  # init the usb repository for the mounting
    network_mode_switch = False  # TODO function to read the Network Mode switch
    tx_switch = False  # TODO function to read the TX/RX switch # to change to set to transmitter or receiver
    if network_mode_switch:
        r_state = STATE_NM
    else:  # Individual Modes
        if tx_switch:  # transmitter
            r_state = STATE_TX_MOUNT_USB
        else:  # receiver
            r_state = STATE_RX_TRANSMISSION_INIT
    return r_state


# ------------ Transmitter state functions ------------ #

def create_mnt_usb_repo():
    cmd = "sudo mkdir /mnt/usb"
    print("\t > " + cmd)
    process = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, encoding="utf-8")
    stderr = process.stderr.read()
    print(stderr, end="")


def mount_usb():
    cmd = "sudo mount -t vfat /dev/sd* /mnt/usb"
    print("\t > " + cmd)
    process = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, encoding="utf-8")
    stderr = process.stderr.read()
    print(stderr, end="")
    if not stderr:  # no error
        return True
    elif "already mounted" in stderr:
        return True
    elif "does not exist" in stderr:
        return False
    else:
        return False


def run_st_tx_mount_usb():
    """ Try to mount the USB """
    # usb_mounted = True  # TODO function to try to mount the USB and return True if the USB is mounted, False else
    usb_mounted = mount_usb()
    if usb_mounted:  # if the usb is mounted, we go to the state copy from usb
        r_state = STATE_TX_COPY_FROM_USB
    else:  # else, we remain in the same state
        r_state = STATE_TX_MOUNT_USB
    return r_state


def run_st_tx_copy_from_usb():
    """ Copy the .txt file from the usb to the working directory under the name NAME_OF_FILE """
    # TODO copy the .txt file from the usb to the working directory under the name NAME_OF_FILE
    print("Looking for the text file:")
    for file in os.listdir(USB_FOLDER):
        if os.path.splitext(file)[1] == ".txt":
            print(file)
            cmd = "sudo cp " + os.path.join(USB_FOLDER, file) + " " + NAME_OF_FILE
            print("\t > " + cmd)
            subprocess.call(cmd, shell=True)
            break
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


def common_transceiver_init():
    RADIO.begin()
    RADIO.setPALevel(RF24_PA_LOW)  # RF24_PA_MIN, RF24_PA_LOW, RF24_PA_HIGH and RF24_PA_MAX
    RADIO.setDataRate(RF24_1MBPS)  # RF24_250KBPS for 250kbs, RF24_1MBPS for 1Mbps, or RF24_2MBPS for 2Mbps
    RADIO.setRetries(1, 15)  # delay (1: 500 µs), retrials number (15: max number)
    RADIO.setAutoAck(True)
    RADIO.enableDynamicPayloads()  # Dynamic ACK enables
    RADIO.setChannel(1)
    RADIO.setCRCLength(RF24_CRC_16)


def run_st_tx_transmission_init():
    """ Initialize the transmitter and the object radio """
    # TODO
    common_transceiver_init()
    RADIO.openWritingPipe(PIPES[0])
    RADIO.openReadingPipe(1, PIPES[1])
    RADIO.stopListening()

    r_frame_num = 0  # we start to send the first message
    r_state = STATE_TX_TRANSMISSION_SEND_MSG
    return r_state, r_frame_num


def run_st_tx_transmission_send_msg(p_list_of_frames, pr_frame_num):
    """ Send one frame from the list of frames """
    # TODO
    frame_to_send = p_list_of_frames[pr_frame_num]
    if RADIO.write(frame_to_send):  # the frame was correctly sent
        pr_frame_num += 1
        if pr_frame_num < len(p_list_of_frames):  # still frames to be sent
            r_state = STATE_TX_TRANSMISSION_SEND_MSG
        else:  # no more frame to be sent
            r_state = STATE_TX_TRANSMISSION_SEND_EOT  # we have to send the end of transmission
    else:
        print("Max number of retries reached, message not sent")
        r_state = STATE_TX_TRANSMISSION_SEND_MSG
    return r_state, pr_frame_num


def run_st_tx_transmission_send_eot():
    """ Send the end of transmission """
    # TODO
    frame_to_send = END_OF_TRANSMISSION
    if RADIO.write(frame_to_send):  # the frame was correctly sent
        r_state = STATE_FINAL
    else:
        print("Max number of retries reached, message not sent")
        r_state = STATE_TX_TRANSMISSION_SEND_EOT
    return r_state


# ------------ Receiver state functions ------------ #

def run_st_rx_transmission_init():
    """ Initialize the receiver and the object radio """
    # TODO
    common_transceiver_init()
    if IRQ_GPIO_PIN is not None:
        # set up callback for irq pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IRQ_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(IRQ_GPIO_PIN, GPIO.FALLING, callback=try_read_data)
    RADIO.openWritingPipe(PIPES[1])
    RADIO.openReadingPipe(1, PIPES[0])
    RADIO.startListening()

    with open("compressed_" + NAME_OF_FILE, "wb") as f:
        f.write(b"")

    r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
    return r_state


def run_st_rx_transmission_receive_msg():
    """ Wait for a message """
    # TODO Check if the received payload corresponds or not to the EOT
    # When we receive a frame, we should send the acknowledgement
    # The frames we receive are appended to a file ("compressed_" + NAME_OF_FILE)
    if RADIO.available():
        r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
        while RADIO.available():  # empty the whole FIFO
            received_msg_length = RADIO.getDynamicPayloadSize()
            received_payload = bytes(RADIO.read(received_msg_length))
            with open("compressed_" + NAME_OF_FILE, "ab") as f:
                f.write(received_payload)
            if received_payload == END_OF_TRANSMISSION:
                RADIO.stopListening()
                r_state = STATE_RX_DECOMPRESS
            else:
                r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
    else:
        print("Radio not available")
        r_state = STATE_RX_TRANSMISSION_RECEIVE_MSG
    return r_state


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
    # usb_mounted = True  # TODO function to try to mount the USB and return True if the USB is mounted, False else
    usb_mounted = mount_usb()
    if usb_mounted:  # if the usb is mounted, we go to the state copy from usb
        r_state = STATE_RX_COPY_TO_USB
    else:  # else, we remain in the same state
        r_state = STATE_RX_MOUNT_USB
    return r_state


def run_st_rx_copy_to_usb():
    """ Copy the .txt file from the working directory to the usb """
    # TODO copy the .txt file from the working directory to the usb
    cmd = "sudo cp " + NAME_OF_FILE + " /mnt/usb/" + NAME_OF_FILE
    print("\t > " + cmd)
    subprocess.call(cmd, shell=True)
    r_state = STATE_FINAL
    return r_state


# ------------ Network Mode state functions ------------ #

def run_st_network_mode():  # TODO
    """ Network Mode """
    r_state = STATE_FINAL
    return r_state
