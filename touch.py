"""TouchPad MP3 Player Demo."""
from time import sleep
from machine import Pin, TouchPad
import _thread


class Touchpad:
    touch = {}
    threshold = {}
    actions = {}
    stop = False
    min_ratio = .1
    max_ratio = .4
    debounce = .1

    def __init__(self, pins):
        for i, pin in enumerate(pins):
            print("Touchpad {}, pin {}".format(i, pin))
            t = TouchPad(Pin(pin))
            try:
                t.read()
                self.touch[i] = t
                self.threshold[i] = []
                self.actions[i] = self.do_nothing
            except Exception as e:
                print("Pin {} no puede ser utilizado. {}".format(pin, str(e)))

    @staticmethod
    def do_nothing():
        pass

    def start_touch_pad_thread(self):
        tp_thread = _thread.start_new_thread(self._sense_touch, ())
        return tp_thread

    def calibrate(self):

        for x in range(12):
            for i in range(len(self.touch)):
                self.threshold[i].append(self.touch[i].read())
                sleep(.1)

        for i in range(len(self.touch)):
            print('Range{0}: {1}-{2}'.format(i, min(self.threshold[i]), max(self.threshold[i])))
            self.threshold[i] = sum(self.threshold[i]) // len(self.threshold[i])
            print('Threshold{0}: {1}'.format(i, self.threshold[i]))

    def _sense_touch(self):
        while not self.stop:

            for i in range(len(self.touch)):
                capacitance = self.touch[i].read()
                cap_ratio = capacitance / self.threshold[i]
                # Check if current TouchPad is pressed
                if i < len(self.touch) and self.min_ratio < cap_ratio < self.max_ratio:

                    sleep(self.debounce)  # Debounce button press
                    print('Pressed {0}: {1}, Diff: {2}, Ratio: {3}%.'.format(
                          i, capacitance,
                          self.threshold[i] - capacitance, cap_ratio * 100))
                    self.actions[i]()

            sleep(.1)
