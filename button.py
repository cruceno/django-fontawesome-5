from machine import Pin, Timer

# def on_pressed(timer):
#     print('pressed')

# def debounce(pin):
    # Start or replace a timer for 200ms, and trigger on_pressed.
    # timer.init(mode=Timer.ONE_SHOT, period=200, callback=on_pressed)

# Register a new hardware timer.
# timer = Timer(0)

# Setup the button input pin with a pull-up resistor.
# button = Pin(0, Pin.IN, Pin.PULL_UP)

# Register an interrupt on rising button input.
# button.irq(debounce, Pin.IRQ_RISING)


class Button:

    def __init__(self, pin):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        self._action = None
        self.timer = Timer(pin)
        self.pin.irq(self.debounce, Pin.IRQ_RISING)

    def debounce(self, irq):
        self.timer.init(mode=Timer.ONE_SHOT, period=650, callback=self.do)

    def do(self, param):
        self._action()

    def set_action(self, method):
        self._action = method
