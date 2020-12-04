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

STATE_TX_MOUNT_USB                    = 10
STATE_TX_COPY_FROM_USB                = 11
STATE_TX_COMPRESS                     = 12
STATE_TX_CREATE_FRAMES_TO_SEND        = 13
STATE_TX_WAIT_FOR_TRANSMISSION_ENABLE = 14
STATE_TX_TRANSMISSION_INIT            = 15
STATE_TX_TRANSMISSION_SEND_MSG        = 16
STATE_TX_TRANSMISSION_SEND_EOT        = 17

STATE_RX_WAIT_FOR_TRANSMISSION_ENABLE = 20
STATE_RX_TRANSMISSION_INIT            = 21
STATE_RX_TRANSMISSION_RECEIVE_MSG     = 22
STATE_RX_DECOMPRESS                   = 23
STATE_RX_TRANSMISSION_SEND_NOK_ACK    = 24
STATE_RX_TRANSMISSION_SEND_OK_ACK     = 25
STATE_RX_MOUNT_USB                    = 26
STATE_RX_COPY_TO_USB                  = 27

STATE_NM = 30


# --------------- Interface Class Definition  ---------------- #

class Switches:
    def __init__(self):
        self.start              = Switch(7)  # when to start (1) the whole program or stop it (0)
        self.en_transmission    = Switch(5)  # to enable the transmission (1) or stop it (0)
        self.Tx                 = Switch(3)  # transmitter (1) or receiver (0)
        self.SRI                = Switch(8)  # Short Range Mode (1) or not (0)
        self.MRM                = Switch(10)  # Mid Range Mode (1) or not (0)
        self.NM                 = Switch(12)  # Network Mode (1) or not (0)

    def update_switches(self):
        self.start.read_switch()
        self.en_transmission.read_switch()
        self.Tx.read_switch()
        self.SRI.read_switch()
        self.MRM.read_switch()
        self.NM.read_switch()


class Switch:
    def __init__(self, p_pin):
        GPIO.setup(p_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
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
        self.start   = LED(13)  # far left
        self.mounted = LED(29)
        self.Tx      = LED(31)
        self.SRI     = LED(33)
        self.MRM     = LED(35)
        self.NM      = LED(37)  # far-right


class LED:
    def __init__(self, p_pin):
        GPIO.setup(p_pin, GPIO.OUT, initial=GPIO.HIGH)  # we specify the initial value  # TODO: might be inverted
        self.pin = p_pin
        # GPIO.output(p_pin, GPIO.HIGH)  # TODO: might be inverted

    def on(self):
        GPIO.output(self.pin, GPIO.LOW)  # TODO: might be inverted

    def off(self):
        GPIO.output(self.pin, GPIO.HIGH)  # TODO: might be inverted

    def get_value(self):
        return GPIO.input(self.pin)

    def toggle(self):
        GPIO.output(self.pin, not self.get_value())


class Interface:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        self.sw = Switches()
        self.led = LEDs()
        self._mode = None

    def get_mode(self):
        """ Returns the mode we're in, using the old position of the switches """
        if self.sw.SRI.was_on() and not any([self.sw.MRM.was_on(), self.sw.NM.was_on()]):
            self._mode = "SRI"
        elif self.sw.MRM.was_on() and not any([self.sw.SRI.was_on(), self.sw.NM.was_on()]):
            self._mode = "MRM"
        elif self.sw.NM.was_on() and not any([self.sw.SRI.was_on(), self.sw.MRM.was_on()]):
            self._mode = "NM"
        else:
            self._mode = None
        return self._mode

    def update(self):
        """ Updates all switch values and sets LEDs, does not change mode """
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


# ----------- Interface Initialisation ----------- #
I_FACE = Interface()


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
    """ Create the message header with on the EOT bit and a counter on 2 bits based on the frame number """
    header = EOT_MASK*eot + (p_frame_num & CNT_MASK)
    r_bytes_header = header.to_bytes(1, "big")
    return r_bytes_header


def split_received_msg(p_received_msg):
    """ Remove the header from the received message and extract from it the EOT bit and the message counter """
    r_received_payload = p_received_msg[1:]
    header = int.from_bytes(p_received_msg[:1], "big")
    r_eot = (header & EOT_MASK) >> EOT_BIT
    r_cnt = header & CNT_MASK
    return r_received_payload, r_eot, r_cnt
