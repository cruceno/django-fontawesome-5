from machine import Pin, Timer


class Button:

    def __init__(self, pin):
        self.pin = Pin(pin, Pin.IN)
        self._action = self._no_action
        self.timer = Timer(pin)
        self.pin.irq(self.debounce, Pin.IRQ_RISING)

    def debounce(self, irq):
        self.timer.init(mode=Timer.ONE_SHOT, period=750, callback=self.do)

    def do(self, param=None):
        self._action()

    def set_action(self, method):
        self._action = method

    def _no_action(self):
        pass


def no_action():
    pass