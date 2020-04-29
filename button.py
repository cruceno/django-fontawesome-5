from machine import Pin, Timer


class Button:

    def __init__(self, pin):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        self._action = None
        self.timer = Timer(pin)
        self.pin.irq(self.debounce, Pin.IRQ_RISING)

    def debounce(self, irq):
        self.timer.init(mode=Timer.ONE_SHOT, period=650, callback=self.do)

    def do(self, param=None):
        self._action(param)

    def set_action(self, method):
        self._action = method


def no_action():
    pass