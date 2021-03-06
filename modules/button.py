from machine import Pin, Timer


class Button:

    def __init__(self, pin, irq=Pin.IRQ_RISING, mode=Pin.IN, pull=Pin.PULL_UP, debounce_time=350):
        self.pin = Pin(pin, mode, pull)
        self._action = self._no_action
        self.timer = Timer(pin)
        self.pin.irq(self.debounce, irq)
        self._params = None
        self._debounce_time = debounce_time

    def debounce(self, irq):
        self.timer.init(mode=Timer.ONE_SHOT, period=self._debounce_time, callback=self.do)

    def do(self, timer):
        timer.deinit()
        if self._params is not None:
            self._action(*self._params)
        else:
            self._action()

    def set_action(self, method, params=None):
        self._params = params
        self._action = method

    def _no_action(self):
        pass

    def clear_action(self):
        self.set_action(self._no_action)

def no_action():
    pass
