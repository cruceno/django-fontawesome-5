import gc
from machine import I2C, Pin, ADC
from esp8266_i2c_lcd import I2cLcd
from button import Button
import time
from utime import sleep_us
import _thread
from machine import UART
from serialapi import SerialAPI
from scales import Scales
from math import log, pow
from statistics import mean, stdev
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
        self.api.add_command('/control/midvaso/toggle', self.toggle_enosc)
        self.api.add_command('/control/midosc/toggle', self.toggle_enosc)

        self.api.add_command('/monitor/midvaso', self.get_midvaso)
        self.api.add_command('/monitor/midosc', self.get_midosc)
        self.api.add_command('/monitor/oscoffset', self.get_osc_offset)
        self.api.add_command('/monitor/bterm', self.read_bterm)
        self.api.add_command('/monitor/vterm', self.read_vterm)

        self.api.add_command('/control/scale/tare', self.load_cell.tare)
        self.api.add_command('/control/scale/set/factor', self.load_cell.set_factor)
        self.api.add_command('/monitor/scale/factor', self.load_cell.get_factor)
        self.api.add_command('/monitor/scale/offset', self.load_cell.get_offset)
        self.api.add_command('/monitor/scale/measure', self.read_load_cell)

        # web = Web()
    #    web.start_web_thread()
        self.vterm = ADC(Pin(34))  # OSC Pin 3
        self.vterm.atten(ADC.ATTN_11DB)
        self.bterm = ADC(Pin(35))  # OSC Pin 9
        self.bterm.atten(ADC.ATTN_11DB)
        self.rfval = ADC(Pin(36))  # OSC Pin 10
        self.rfval.atten(ADC.ATTN_6DB)


        # DIGITAL OUTPUTS (value 0 is power on value 1 is power of)
        self.enosc = Pin(5, Pin.OUT, value=1)  # OSC Pin 2
        self.midvaso = Pin(4, Pin.OUT, value=1)  # OSC Pin 6
        self.midosc = Pin(15, Pin.OUT, value=0)  # OSC Pin 8
        self.value = 0

        self.func = 0

        self.btn1 = Button(27)
        self.btn1.set_action(self.debug_page)
        self.btn2 = Button(14)
        self.btn2.set_action(self.lcd_on_off)
        self.btn3 = Button(12)
        self.btn3.set_action(self.home)

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

    def set_off_osc(self):
        self.enosc.value(1)  # Deshabilita enosc
        self.midosc.value(1)  # Deshabilita midosc
        self.midvaso.value(1)  # Deshabilita midvaso
        sleep_us(100)

    def enable_midosc(self):
        self.enosc.value(0) # Habilita oscilador
        self.midvaso.value(1) # Deshabilita midvaso
        self.midosc.value(0) # Habilita midosc
        sleep_us(100)

    def enable_midvaso(self):
        self.enosc.value(0) # Habilita oscilador
        self.midvaso.value(0) # Habilita midvaso
        self.midosc.value(1) # Deshabilita midosc
        sleep_us(100)

    def get_midosc(self):
        self.enable_midosc()
        rf = self.read_adc(self.rfval, 2.0)
        while rf[1] > 1:
            rf = self.read_adc(self.rfval, 2.0)
        self.set_off_osc()
        return rf

    def get_midvaso(self):
        self.enable_midvaso()
        rf = self.read_adc(self.rfval, 2.0)
        while rf[1] > 1:
            rf = self.read_adc(self.rfval, 2.0)
        self.set_off_osc()
        return rf

    def get_osc_offset(self):
        self.set_off_osc()
        rf = self.read_adc(self.rfval, 2.0)
        while rf[1] > 1:
            rf = self.read_adc(self.rfval, 2.0)
        return rf

    def get_relation(self):
        offset = self.get_osc_offset()[0]
        midvaso = self.get_midvaso()[0]
        midosc = self.get_midosc()[0]
        return int((midvaso-offset)/(midosc-offset)*1024)

    def toggle_func(self):

        if self.func == 0:
            self.func = 1  # Funcion medir oscilador

        elif self.func == 1:
            self.func = 2  # Funcion medir vaso

        elif self.func == 2:
            self.func = 3

        elif self.func == 3:
            self.func = 0


    def read_adc(self, adc, vref, n=100):
        values = []
        for i in range(0, n):
            read = adc.read()
            values.append(read)
            acum = (read - values[i-1])/n + values[i-1]
            values[i] = acum
            sleep_us(2)

        prom = mean(values)
        deviation = stdev(values, prom)

        conv = vref/4096
        rf_round = 3

        return int(prom), int(deviation), round(prom*conv, rf_round),\
               round(deviation*conv, rf_round)

    def read_bterm(self):
        adc = self.read_adc(self.bterm, vref=3.3, n=5)[0]
        return round(self.adc_to_temp(adc), 1)

    def read_vterm(self):
       # -0,0279
       # 5776
        adc = self.read_adc(self.vterm, vref=3.3, n=5)[0]
        return round(self.adc_to_temp(adc), 1)        # self.tp.actions[2] = self.home

    @staticmethod
    def adc_to_temp(adc):
        return log(adc/5776)/-0.0279

    def read_load_cell(self, json=False):

        return ', '.join(str(s) for s in self.load_cell.averaged_w())+'\n'

    def debug_thread(self):
        self.lcd.clear()
        self.lcd.putstr("RF{}:     VT:    P:       BT:    ".format(self.func))
        rf = 0
        vt = 0
        bt = 0
        lc = 0

        while not self.stop:
            self.lcd.move_to(2,0)
            self.lcd.putstr(str(self.func))
            self.lcd.move_to(4, 0)
            rf = str(rf)
            self.lcd.putstr(rf if len(rf) == 4 else rf+' '*(4-len(rf)))
            self.lcd.move_to(12, 0)
            vt = str(vt)
            self.lcd.putstr(vt if len(vt) == 4 else vt+' '*(4-len(vt)))
            self.lcd.move_to(3,1)
            lc = str(lc)
            self.lcd.putstr(lc if len(lc) == 5 else lc+' '*(5-len(lc)))
            self.lcd.move_to(12,1)
            bt = str(bt)
            self.lcd.putstr(bt if len(bt) == 4 else bt+' '*(4-len(bt)))

            if self.func == 0:
                rf = self.get_relation()
            elif self.func == 1:
                rf = self.get_midosc()[0]
            elif self.func == 2:
                rf = self.get_midvaso()[0]
            elif self.func == 3:
                rf = self.get_osc_offset()[0]

            vt = self.read_vterm()
            bt = self.read_bterm()
            lc = int(self.load_cell.averaged_w(samples=10)[0])

            time.sleep(.1)

    def debug_page(self):
        self.stop = False
        self.set_off_osc()
        self.func = 0
        self.btn1.set_action(self.toggle_func)
        # self.tp.actions[1] =
        self.btn3.set_action(self.home)
        _thread.start_new_thread(self.debug_thread, ())

    def home(self):
        self.stop = True
        self.btn1.set_action(self.step_1)
        self.btn3.set_action(self.debug_page)
        self.set_off_osc()
        self.lcd.clear()
        self.lcd.putstr("    DELVER    \nIniciar -- Debug")

    def step_1(self):
        self.stop = True
        self.btn1.set_action(self.home)
        self.btn3.set_action(self.process_1)
        self.lcd.clear()
        self.lcd.putstr("Vaciar vaso  \nCancelar --  OK")

    def process_1(self):

        self.btn1.set_action(self.no_action)
        self.btn3.set_action(self.no_action)
        self.lcd.clear()
        self.lcd.putstr("Midiendo   \n                ")
        self.value = 0
        while self.value == 0:
            self.value = self.get_relation()
            time.sleep(.1)

        self.midosc.value(1)
        self.lcd.clear()
        self.lcd.putstr("Valor:{}    \nCancelar --  OK".format(self.value))
        self.btn1.set_action(self.home)
        self.btn3.set_action(self.step_2)

    def step_2(self):

        self.btn1.set_action(self.home)
        self.btn3.set_action(self.process_2)
        self.lcd.clear()
        self.lcd.putstr("Llene y enrase\nCancelar --  OK")

    def process_2(self):

        self.btn1.set_action(self.no_action)
        self.btn3.set_action(self.no_action)
        self.lcd.clear()
        self.lcd.putstr("Midiendo \n                ")
        value = self.get_relation()
        medicion = int(value/self.value*1024)
        self.lcd.clear()
        self.lcd.putstr("Medicion:{} \n{}/{}".format(medicion,
                                                     value,
                                                     self.value))
        self.lcd.move_to(13,1)
        self.lcd.putstr('OK')

        self.btn1.set_action(self.no_action)
        self.btn3.set_action(self.home)

delver = Delver(i2c, scale, api)

delver.load_cell.set_factor(1780745.0 / 998)

def run_in_trhead():
    while True:
        api.read_command()
        time.sleep(.2)
        gc.collect()

mainthread = _thread.start_new_thread(run_in_trhead,())





