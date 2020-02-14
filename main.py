import gc
from machine import I2C, Pin, ADC
from esp8266_i2c_lcd import I2cLcd
from touch import Touchpad
import time
import _thread
from machine import UART
from serialapi import SerialAPI
from scales import Scales

uart = UART(2, 9600)
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=400000)
scale = Scales(d_out=23, pd_sck=19)
api = SerialAPI(uart)

class Delver:

    def __init__(self, i2c, scale, api):
        self.lcd = I2cLcd(i2c, 0x27, 2, 16)
        self.load_cell = scale
        self.api = api
        self.api.add_command('/control/enosc/toggle', self.toggle_enosc)
        self.api.add_command('/control/midvaso/toggle', self.toggle_midvaso)
        self.api.add_command('/control/midosc/toggle', self.toggle_midosc)
        self.api.add_command('/monitor/bterm', self.read_bterm)
        self.api.add_command('/monitor/vterm', self.read_vterm)
        self.api.add_command('/control/scale/tare', self.load_cell.tare)
        self.api.add_command('/monitor/scale/measure', self.read_load_cell)

        # web = Web()
    #    web.start_web_thread()
        self.vterm = ADC(Pin(34))  # OSC Pin 3
        self.vterm.atten(ADC.ATTN_11DB)
        self.bterm = ADC(Pin(35))  # OSC Pin 9
        self.bterm.atten(ADC.ATTN_11DB)
        self.rfval = ADC(Pin(36))  # OSC Pin 10
        self.rfval.atten(ADC.ATTN_0DB)

        # DIGITAL OUTPUTS (value 0 is power on value 1 is power of)
        self.enosc = Pin(5, Pin.OUT, value=1)  # OSC Pin 2
        self.midvaso = Pin(4, Pin.OUT, value=1)  # OSC Pin 6
        self.midosc = Pin(15, Pin.OUT, value=0)  # OSC Pin 8
        self.value = 0

        self.func = 0
        self.tp = Touchpad([27, 14, 12])
        self.tp.debounce = .4
        self.tp.calibrate()
        self.tp.start_touch_pad_thread()
        self.tp.actions[1] = self.lcd_on_off
        self.stop = True
        self.stable_time = 4
        self.LCD_STATE = True
        self.home()

    def lcd_on_off(self):
        if self.LCD_STATE:
            self.lcd.backlight_off()
            self.lcd.display_off()
            self.LCD_STATE = False
        else:
            self.lcd.backlight_on()
            self.lcd.display_on()
            self.LCD_STATE = True

    def no_action(self):
        pass

    def toggle_enosc(self):
        self.enosc.on() if self.enosc.value() == 0 else self.enosc.off()

    def toggle_midosc(self):
        self.midosc.on() if self.midosc.value() == 0 else self.midosc.off()

    def toggle_midvaso(self):
        self.midvaso.on() if self.midvaso.value() == 0 else self.midvaso.off()

    def toggle_func(self):

        if self.func == 0:
            self.func = 1 # Funcion medir oscilador
            self.enosc.value(0) # Habilita oscilador
            self.midvaso.value(1) # Deshabilita midvaso
            self.midosc.value(0) # Habilita midosc

        elif self.func == 1:
            self.func = 2 # Funcion medir vaso
            self.enosc.value(0) # Habilita enosc
            self.midosc.value(1) # Deshabilita midosc
            self.midvaso.value(0) # Habilita midvaso

        else:
            self.set_off_osc()

    def set_off_osc(self):
        self.func = 0  # Funcion apagado
        self.enosc.value(1)  # Deshabilita enosc
        self.midosc.value(1)  # Deshabilita midosc
        self.midvaso.value(1)  # Deshabilita midvaso

    def read_adc(self, adc, n=10):
        value = 0
        for i in range(0, n):
            value += adc.read()
            time.sleep(.01)
        prom = int(value/n)
        #Sumamos 100 para que de igual que delver
        #TODO:sacar esos 100 de la suma
        offset = 0 if self.enosc.value() == 1 else 100
        return prom

    def read_bterm(self):
        return self.read_adc(self.bterm)

    def read_vterm(self):
        return self.read_adc(self.vterm)

    def read_load_cell(self, json=False):

        return ', '.join(str(s) for s in self.load_cell.averaged_w())+'\n'

    def debug_thread(self):
        self.lcd.clear()
        self.lcd.putstr("RF:      VT:    F:           END")
        rf = 0
        vt = 0

        while not self.stop:
            self.lcd.move_to(3, 0)
            rf = str(rf)
            self.lcd.putstr(rf if len(rf) == 4 else rf+' '*(4-len(rf)))
            self.lcd.move_to(12, 0)
            vt = str(vt)
            self.lcd.putstr(vt if len(vt) == 4 else vt+' '*(4-len(vt)))
            self.lcd.move_to(2,1)
            self.lcd.putstr(str(self.func))
            rf = self.read_adc(self.rfval, 25)
            vt = self.read_adc(self.vterm, 5)
            time.sleep(.2)

    def debug_page(self):
        self.stop = False
        self.set_off_osc()
        self.func = 0
        self.tp.actions[0] = self.toggle_func
        # self.tp.actions[1] =
        self.tp.actions[2] = self.home
        _thread.start_new_thread(self.debug_thread, ())

    def home(self):
        self.stop = True
        self.tp.actions[0] = self.step_1
        self.tp.actions[2] = self.debug_page
        self.set_off_osc()
        self.lcd.clear()
        self.lcd.putstr("    DELVER    \nIniciar -- Debug")

    def step_1(self):
        self.stop = True
        self.tp.actions[0] = self.home
        self.tp.actions[2] = self.process_1
        self.lcd.clear()
        self.lcd.putstr("Vaciar vaso  \nCancelar --  OK")

    def process_1(self):

        self.tp.actions[0] = self.no_action
        self.tp.actions[2] = self.no_action
        self.lcd.clear()
        self.lcd.putstr("Midiendo   \n                ")
        self.value = 0
        self.enosc.value(0)
        self.midosc.value(0)

        for x in range(8, 15):
            self.lcd.move_to(x, 0)
            self.lcd.putchar(".")
            time.sleep(self.stable_time/15)

        while self.value == 0:
            self.value = self.read_adc(self.rfval, 100)
            time.sleep(.1)

        self.midosc.value(1)
        self.lcd.clear()
        self.lcd.putstr("Valor:{}    \nCancelar --  OK".format(self.value))
        self.tp.actions[2] = self.step_2

    def step_2(self):

        self.tp.actions[0] = self.home
        self.tp.actions[2] = self.process_2
        self.lcd.clear()
        self.lcd.putstr("Llene y enrase\nCancelar --  OK")

    def process_2(self):
        self.tp.actions[0] = self.no_action
        self.tp.actions[2] = self.no_action
        self.lcd.clear()
        self.lcd.putstr("Midiendo \n                ")
        value = 0
        self.enosc.value(0)
        self.midvaso.value(0)

        for x in range(8, 15):
            self.lcd.move_to(x, 0)
            self.lcd.putchar(".")
            time.sleep(self.stable_time / 15)
        value = self.read_adc(self.rfval, 100)
        self.midvaso.value(1)
        medicion = round(value/self.value,2)
        self.lcd.clear()
        self.lcd.putstr("Medicion:{} \n{}/{}".format(medicion,
                                                     value,
                                                     self.value))
        self.lcd.move_to(13,1)
        self.lcd.putstr('OK')
        self.tp.actions[2] = self.home

delver = Delver(i2c, scale, api)
delver.load_cell.factor = 1780745.0 / 998

def run_in_trhead():
    while True:
        api.read_command()
        time.sleep(.2)
        gc.collect()

mainthread = _thread.start_new_thread(run_in_trhead,())

# scales.tare()
# val = scales.stable_value()
# print(val)
# scales.power_off()





