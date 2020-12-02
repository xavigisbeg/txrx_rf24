# -*- coding: utf-8 -*-

import subprocess
import RPi.GPIO as GPIO


# ------------ Constants Definition ------------ #

# USB_FOLDER = "/media/usb0"
USB_FOLDER = "/mnt/usb"


# ------------ States Definition ------------ #

STATE_FINAL         = 0
STATE_INIT          = 1
STATE_READ_SWITCHES = 2

STATE_TX_MOUNT_USB             = 10
STATE_TX_COPY_FROM_USB         = 11
STATE_TX_COMPRESS              = 12
STATE_TX_CREATE_FRAMES_TO_SEND = 13
STATE_TX_TRANSMISSION_INIT     = 14
STATE_TX_TRANSMISSION_SEND_MSG = 15
STATE_TX_TRANSMISSION_SEND_EOT = 16

STATE_RX_TRANSMISSION_INIT         = 20
STATE_RX_TRANSMISSION_RECEIVE_MSG  = 21
STATE_RX_DECOMPRESS                = 22
STATE_RX_TRANSMISSION_SEND_NOK_ACK = 23
STATE_RX_TRANSMISSION_SEND_OK_ACK  = 24
STATE_RX_MOUNT_USB                 = 25
STATE_RX_COPY_TO_USB               = 26

STATE_NM = 30


# --------------- Interface  ---------------- #

class Switches:
    def __init__(self):
        self.start              = Switch(10)  # when to start (1) the whole program or stop it (0)
        self.en_transmission    = Switch(11)  # to enable the transmission
        self.Tx                 = Switch(12)  # transmitter (1) or receiver (0)
        self.SRI                = Switch(13)  # Short Range Mode (1) or not (0)
        self.MRM                = Switch(14)  # Mid Range Mode (1) or not (0)
        self.NM                 = Switch(15)  # Network Mode (1) or not (0)

    def update_switches(self):
        self.start.read_switch()
        self.en_transmission.read_switch()
        self.Tx.read_switch()
        self.SRI.read_switch()
        self.MRM.read_switch()
        self.NM.read_switch()


class Switch:
    def __init__(self, p_pin):
        GPIO.setup(p_pin, GPIO.IN)
        self.pin = p_pin
        self.value = GPIO.input(p_pin)

    def read_switch(self):
        self.value = GPIO.input(self.pin)  # TODO: might be inverted

    def is_on(self):
        self.read_switch()
        return self.value

    def was_on(self):
        return self.value


class LEDs:
    def __init__(self):
        self.start   = LED(16)
        self.mounted = LED(17)
        self.Tx      = LED(18)
        self.SRI     = LED(19)
        self.MRM     = LED(20)
        self.NM      = LED(21)


class LED:
    def __init__(self, p_pin):
        GPIO.setup(p_pin, GPIO.IN)
        self.pin = p_pin
        self.value = GPIO.output(p_pin, GPIO.LOW)  # TODO: might be inverted

    def on(self):
        GPIO.output(self.pin, GPIO.HIGH)  # TODO: might be inverted

    def off(self):
        GPIO.output(self.pin, GPIO.LOW)  # TODO: might be inverted


class Interface:

    def __init__(self):
        GPIO.setmode(GPIO.BOARD)
        self.sw = Switches()
        self.led = LEDs()
        self._mode = None

    def get_mode(self):  # TODO: Decide if mode is updated anytime, so it happens every update and remove first line
        self.update()
        if self.sw.SRI.is_on() and not any([self.sw.MRM.is_on(), self.sw.NM.is_on()]):
            self._mode = "SRI"
        elif self.sw.MRM.is_on() and not any([self.sw.SRI.is_on(), self.sw.NM.is_on()]):
            self._mode = "MRM"
        elif self.sw.NM.is_on() and not any([self.sw.SRI.is_on(), self.sw.MRM.is_on()]):
            self._mode = "NM"
        else:
            self._mode = None
        return self._mode

    def update(self):
        """Updates all switch values and sets LEDs, does not change mode"""
        self.sw.update_switches()

        if self.sw.start.is_on(): self.led.start.on()  # TODO: Enable and start combined usage
        else: self.led.start.off()

        if self.sw.Tx.is_on(): self.led.Tx.on()
        else: self.led.Tx.off()

        if self.sw.SRI.is_on(): self.led.SRI.on()
        else: self.led.SRI.off()

        if self.sw.MRM.is_on(): self.led.MRM.on()
        else: self.led.MRM.off()

        if self.sw.NM.is_on(): self.led.NM.on()
        else: self.led.NM.off()


# --------------- USB Management  ---------------- #

def check_mounted_usb():  # TODO use USBmount, so the USB will be auto-mounted
    # If the directory USB_FOLDER does not exist, create it
    cmd = "[ ! -d \"" + USB_FOLDER + "\" ] && sudo mkdir -p " + USB_FOLDER
    print("\t > " + cmd)
    subprocess.call(cmd, shell=True)

    # Mount the USB to the USB_FOLDER
    cmd = "sudo mount -t vfat /dev/sd* " + USB_FOLDER
    print("\t > " + cmd)
    process = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, encoding="utf-8")
    stderr = process.stderr.read()
    print(stderr, end="")
    if not stderr:  # no error
        return True
    elif "already mounted" in stderr:  # the USB is already mounted
        return True
    elif "does not exist" in stderr:  # there is no USB plugged
        return False
    else:
        return False


# --------------- Message Headers --------------- #
EOT_BIT = 7
EOT_MASK = 1 << EOT_BIT
CNT_MASK = 0b11


def create_header(p_frame_num, eot=False):
    """ Create the message header with on the EOT bit and a counter on 4 bits based on the frame number """
    header = EOT_MASK*eot + (p_frame_num & CNT_MASK)
    r_bytes_header = header.to_bytes(1, "big")
    return r_bytes_header


def split_received_msg(p_received_msg):
    """ Remove the header from the received message and extract from it the EOT bit and the message counter """
    r_received_payload = p_received_msg[1:]
    header = int.from_bytes(p_received_msg[:1], "big")
    r_eot = (header & EOT_MASK) >> EOT_BIT
    r_cnt = header & CNT_MASK
    # print(f"header: {header:#011_b}, EOT: {r_eot:b}, counter: {r_cnt:06_b}")
    return r_received_payload, r_eot, r_cnt
