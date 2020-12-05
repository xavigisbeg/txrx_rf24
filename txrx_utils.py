# -*- coding: utf-8 -*-

import os
import subprocess

import RPi.GPIO as GPIO


# ------------ Constants Definition ------------ #

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
        # start           -> when to start (1) the whole program or stop it (0)
        self.start           = Switch(7)
        # en_transmission -> to enable the transmission (1) or stop it (0) | in NM when 0, try to copy to USB
        self.en_transmission = Switch(5)
        # Tx              -> transmitter (1) or receiver (0) | in NM when 1, try to copy from USB and be the first node
        self.Tx              = Switch(3)
        # SRI             -> Short Range Mode (1) or not (0)
        self.SRI             = Switch(8)
        # MRM             -> Mid Range Mode (1) or not (0)
        self.MRM             = Switch(10)
        # NM              -> Network Mode (1) or not (0)
        self.NM              = Switch(12)

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
        self.value = not GPIO.input(self.pin)

    def is_on(self):
        self.read_switch()
        return self.value

    def was_on(self):
        return self.value


class LEDs:
    def __init__(self):
        # start         -> the process has started with the start switch ON
        self.start        = LED(13)  # GREEN    far left
        # mounted       -> USB correctly mounted
        self.mounted      = LED(29)  # BLUE
        # ready         -> Tx ready to send or Rx ready to copy to USB | in NM, got all messages
        self.ready        = LED(31)  # GREEN
        # transmission  -> blink in transmission every 50 frames | in NM, toggled when sending
        self.transmission = LED(33)  # RED
        # reboot        -> ON when rebooting | in NM, when synchronized
        self.reboot       = LED(35)  # RED
        # success       -> success on Tx (OK received) or on Rx (file uploaded)
        self.success      = LED(37)  # RED      far-right

    def all_off(self):
        self.start.off()
        self.mounted.off()
        self.ready.off()
        self.transmission.off()
        self.reboot.off()
        self.success.off()


class LED:
    def __init__(self, p_pin):
        GPIO.setup(p_pin, GPIO.OUT, initial=GPIO.LOW)  # we instantiate the LED with an initial value
        self.pin = p_pin

    def on(self):
        GPIO.output(self.pin, GPIO.HIGH)

    def off(self):
        GPIO.output(self.pin, GPIO.LOW)

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


# ----------- Interface Initialisation ----------- #
I_FACE = Interface()


# --------------- USB Management  ---------------- #

def mount_usb():
    """ Try to mount the USB and return True if success """
    # If the directory USB_FOLDER does not exist, create it
    cmd = "[ ! -d \"" + USB_FOLDER + "\" ] && sudo mkdir -p " + USB_FOLDER
    print("\t > " + cmd)
    subprocess.call(cmd, shell=True)

    # Check the sd* devices available
    cmd = "ls /dev/sd*"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, encoding="utf-8")
    stdout = process.stdout.read().strip()
    # Try to mount any sd* USB to the USB_FOLDER
    for sd in stdout.split():
        cmd = "sudo mount " + sd + " " + USB_FOLDER
        print("\t > " + cmd)
        process = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, encoding="utf-8")
        stderr = process.stderr.read().strip()
        print(stderr)
        if not stderr:  # no error
            return True
        elif stderr.endswith(f"{sd} already mounted on {USB_FOLDER}."):  # the USB is already mounted
            return True
    return False


def get_proper_txt_file(input_file, mode):
    """ Return if possible the text file on the USB corresponding to the mode """
    # Get the list of text files
    list_txt_files = list()
    for file in os.listdir(USB_FOLDER):
        if os.path.splitext(file)[1] == ".txt":
            list_txt_files.append(file)

    # Find a text file on the USB that corresponds to what is expected
    ending = "NM-TX" if mode == "NM" else mode + "-B-TX"
    file = None
    if len(list_txt_files) > 0:  # if there is at least one txt file
        if len(list_txt_files) == 1:  # if there is only one txt file on the USB
            file = list_txt_files[0]
        elif input_file in list_txt_files:  # if there is a txt file corresponding to the expected name
            file = input_file
        else:
            for test_file in list_txt_files:
                if os.path.splitext(test_file)[0].endswith(ending):  # if its name ends as expected
                    file = test_file
    return file


def unmount_usb():
    """ Unmount the USB """
    cmd = "sudo umount " + USB_FOLDER
    print("\t > " + cmd)
    subprocess.call(cmd, shell=True)


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
