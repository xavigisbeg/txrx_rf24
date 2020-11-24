# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO

# ------------ States Definition ------------ #

STATE_FINAL         = 0
STATE_INIT          = 1
STATE_READ_SWITCHES = 2

STATE_TX_MOUNT_USB                    = 3
STATE_TX_COPY_FROM_USB                = 4
STATE_TX_COMPRESS                     = 5
STATE_TX_CREATE_FRAMES_TO_SEND        = 6
STATE_TX_TRANSMISSION_INIT            = 7
STATE_TX_TRANSMISSION_SEND_MSG        = 8
STATE_TX_TRANSMISSION_RECEIVE_ACK     = 9
STATE_TX_TRANSMISSION_SEND_EOT        = 10
STATE_TX_TRANSMISSION_RECEIVE_EOT_ACK = 11

STATE_RX_TRANSMISSION_INIT        = 12
STATE_RX_TRANSMISSION_RECEIVE_MSG = 13
STATE_RX_DECOMPRESS               = 14
STATE_RX_MOUNT_USB                = 15
STATE_RX_COPY_TO_USB              = 16

STATE_NM = 17

# --------------- Interface  ---------------- #


class Switches:
    def __init__(self):
        self.start              = Switch(10)
        self.en_transmission    = Switch(11)  # yet undefined
        self.Tx                 = Switch(12)
        self.SRI                = Switch(13)
        self.MRM                = Switch(14)
        self.NM                 = Switch(15)


    def update_switches(self):
        self.start.read_switch()
        self.enableTx.read_switch()
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
        self.start      = LED(16)
        self.mounted    = LED(17)
        self.Tx         = LED(18)
        self.SRI        = LED(19)
        self.MRM        = LED(20)
        self.NM         = LED(21)


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
            self._mode = 'SRI'
        elif self.sw.MRM.is_on() and not any([self.sw.SRI.is_on(), self.sw.NM.is_on()]):
            self._mode = 'MRM'
        elif self.sw.NM.is_on() and not any([self.sw.SRI.is_on(), self.sw.MRM.is_on()]):
            self._mode = 'NM'
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
