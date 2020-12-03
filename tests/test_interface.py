import RPi.GPIO as GPIO

class Switches:
    def __init__(self):
        self.start              = Switch(7)  # when to start (1) the whole program or stop it (0)
        self.en_transmission    = Switch(5)  # to enable the transmission
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
        self.start   = LED(13)  # 37
        self.mounted = LED(29)  # 35
        self.Tx      = LED(31)  # 33
        self.SRI     = LED(33)  # 31
        self.MRM     = LED(35)  # 29
        self.NM      = LED(37)  # 13


class LED:
    def __init__(self, p_pin):
        GPIO.setup(p_pin, GPIO.OUT)
        self.pin = p_pin
        self.value = GPIO.output(p_pin, GPIO.HIGH)  # TODO: might be inverted

    def on(self):
        GPIO.output(self.pin, GPIO.LOW)  # TODO: might be inverted

    def off(self):
        GPIO.output(self.pin, GPIO.HIGH)  # TODO: might be inverted


class Interface:

    def __init__(self):
        GPIO.setwarnings(False)
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

        if self.sw.en_transmission.is_on(): self.led.mounted.on()
        else: self.led.mounted.off()

        if self.sw.Tx.is_on(): self.led.Tx.on()
        else: self.led.Tx.off()

        if self.sw.SRI.is_on(): self.led.SRI.on()
        else: self.led.SRI.off()

        if self.sw.MRM.is_on(): self.led.MRM.on()
        else: self.led.MRM.off()

        if self.sw.NM.is_on(): self.led.NM.on()
        else: self.led.NM.off()

    def identify(self):
        for sw in [self.sw.start, self.sw.en_transmission, self.sw.Tx, self.sw.SRI, self.sw.MRM, self.sw.NM]:
            if sw.is_on():
                self.led.start.on()
            while sw.is_on():
                pass
            self.led.start.off()


def test_interface():
    try:
        iface = Interface()
        while True:
            iface.update()  # iface.update()
    except KeyboardInterrupt:
        GPIO.cleanup()


if __name__ == "__main__":
    test_interface()


"""import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup([13, 29, 31, 33, 35, 37], GPIO.OUT)
GPIO.setup([7, 5, 3, 8, 10, 12], GPIO.IN)
GPIO.output([13, 29, 31, 33, 35, 37], GPIO.HIGH)
GPIO.output([13, 29, 31, 33, 35, 37], GPIO.LOW)
def update():
    a = []
    for i in [7, 5, 3, 8, 10, 12]:
        a.append(GPIO.input(i))
    return a
"""
