import gc
from machine import I2C, Pin, ADC
from esp8266_i2c_lcd import I2cLcd
from button import Button, no_action
import time
from utime import sleep_us, sleep
import _thread
from machine import UART
from serialapi import SerialAPI
from scales import Scales
from math import log
from statistics import mean, stdev
from config import load_config, update_config, save_config
from materials import material_from_code, add_material, remove_material, Material, next_material
from calculations import medicion_grano

uart = UART(2, 115200)
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=400000)
scale = Scales(d_out=23, pd_sck=19)
api = SerialAPI(uart)
lcd = I2cLcd(i2c, 0x27, 2, 16)


class Delver:
    def __init__(self, lcd, scale):
        self.config = load_config()
        self.kalvaso = self.config['rf']['calibration']
        self.lcd = lcd
        self.load_cell = scale
        self.load_cell.set_factor(self.config['load_cell']["calibration_factor"])

        self.vterm = ADC(Pin(34))  # OSC Pin 3
        self.vterm.atten(ADC.ATTN_11DB)

        self.bterm = ADC(Pin(35))  # OSC Pin 9
        self.bterm.atten(ADC.ATTN_11DB)

        self.rfval = ADC(Pin(36))  # OSC Pin 10
        self.rfval.atten(ADC.ATTN_11DB)

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
        self.current_material = Material()
        self.previous_material = "000"
        self.fav_index = 0
        self.home()

    def read_adc(self, adc, vref, n=100, delay_us=10):
        values = []
        for i in range(0, n):
            read = adc.read()
            values.append(read)
            acum = (read - values[i-1])/n + values[i-1]
            values[i] = acum
            sleep_us(delay_us)

        prom = mean(values)
        deviation = stdev(values, prom)

        conv = vref/4096
        rf_round = 3

        return int(prom), int(deviation), round(prom*conv, rf_round), \
               round(deviation*conv, rf_round)

    def lcd_on_off(self):
        if self.LCD_STATE:
            self.lcd.backlight_off()
            self.lcd.display_off()
            self.LCD_STATE = False
        else:
            self.lcd.backlight_on()
            self.lcd.display_on()
            self.LCD_STATE = True

    # RF functions
    def read_rf(self, samples=None, delay=None):

        samples = self.config["rf"]["samples"] if samples is None else samples
        delay = self.config["rf"]["delay"] if delay is None else delay

        read = self.read_adc(self.rfval, vref=3.6, n=samples, delay_us=delay)
        while read[1] > 1:
            read = self.read_adc(self.rfval, vref=3.6, n=samples, delay_us=delay)

        return read

    def set_osc(self, e, o, v):
        self.enosc.value(e)  # Deshabilita enosc
        self.midosc.value(o)  # Deshabilita midosc
        self.midvaso.value(v) # Deshabilita midvaso
        sleep_us(100)

    def set_off_osc(self):
        self.set_osc(True, True, True)

    def enable_midosc(self):
        self.set_osc(False, False, True)

    def enable_midvaso(self):
        self.set_osc(False, True, False)

    def get_midosc(self):
        self.enable_midosc()
        rf = self.read_rf()
        self.set_off_osc()
        return rf

    def get_midvaso(self):
        self.enable_midvaso()
        rf = self.read_rf()
        self.set_off_osc()
        return rf

    def get_osc_offset(self):
        self.set_off_osc()
        rf = self.read_rf()
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
            self.func = 4

        elif self.func == 4:
            self.func = 0

    ## Temperature functions
    def read_bterm(self):
        adc = self.read_adc(self.bterm, vref=3.6, n=5)[0]
        return round(self.adc_to_temp(adc), 1)

    def read_vterm(self):
       # -0,0279
       # 5776
        adc = self.read_adc(self.vterm, vref=3.6, n=5)[0]
        return round(self.adc_to_temp(adc), 1)        # self.tp.actions[2] = self.home

    @staticmethod
    def adc_to_temp(adc, a=5776, b=-0.0279):
        # print(adc, a, b)
        return log(adc/a)/b if adc != 0 else 0

    ## Display pages
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
            if self.func == 4:
                adj = 2.25 - (self.read_vterm()-22)*7.9/1000
                adj = "{0:.3f}".format(adj)
                self.lcd.putstr(adj if len(adj) == 5 else adj+' '*(5-len(adj)))
            else:
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
            elif self.func == 4:
                rf = self.get_midosc()[2]

            vt = self.read_vterm()
            bt = self.read_bterm()
            lc = int((self.load_cell.get_value(samples=10, delay=10)[0]) * self.load_cell.get_factor())
            time.sleep(.1)

    def debug_page(self):
        self.stop = False
        self.set_off_osc()
        self.func = 0
        self.btn1.set_action(self.toggle_func)
        # self.tp.actions[1] =
        self.btn3.set_action(self.home)
        self.btn2.set_action(self.load_cell.tare(self.config["load_cell"]["samples"],
                                                 self.config["load_cell"]["delay"])
                             )
        _thread.start_new_thread(self.debug_thread, ())

    def home(self):
        self.stop = True
        self.current_material = Material()
        self.fav_index = 0
        self.btn1.set_action(self.select_favourite_material)
        self.btn3.set_action(self.debug_page)
        self.set_off_osc()
        self.lcd.clear()
        self.lcd.putstr("    DELVER    \nIniciar -- Debug")

    def select_favourite_material(self):
        self.btn1.set_action(self.select_favourite_material)
        self.btn2.set_action(self.home)
        self.lcd.clear()
        self.lcd.putstr('! Buscando        material !')
        if self.fav_index <= 9:
            self.current_material = material_from_code(self.config["materials"][self.fav_index])
            name = self.current_material.name
            self.fav_index = self.fav_index + 1
            name = name[0:14] if len(name) > 15 else name
            self.lcd.clear()
            screen = name+'\n'+"Next  Back  Ok"
            self.lcd.putstr(screen)
            self.btn3.set_action(self.step_1)

        else:
            self.lcd.clear()
            self.btn3.set_action(self.select_material)
            self.current_material = Material()
            self.lcd.putstr("  Ver  todos \n      Back    Ok")

    def select_material(self):
        self.fav_index = 0
        self.lcd.clear()
        self.lcd.putstr('! Buscando        material !')
        if not self.current_material.code:
            self.current_material = next_material("000")
        else:
            self.current_material = next_material(self.current_material.code)

        self.btn1.set_action(self.select_material)
        self.btn2.set_action(self.select_favourite_material)
        self.btn3.set_action(self.step_1)
        self.lcd.clear()

        name = self.current_material.name
        name = name[0:14] if len(name) > 15 else name
        self.lcd.putstr(name+'\n'+"Next  Back  Ok")

    def step_1(self):
        self.stop = True
        self.btn1.set_action(self.home)
        self.btn3.set_action(self.process_1)
        self.lcd.clear()
        self.lcd.putstr("Vaciar vaso  \nCancelar --  OK")

    def process_1(self):

        self.btn1.set_action(no_action)
        self.btn3.set_action(no_action)
        self.lcd.clear()
        self.lcd.putstr("Midiendo... \n                ")
        self.value = 0
        self.load_cell.tare(self.config["load_cell"]["samples"], self.config["load_cell"]["delay"])
        while self.value == 0:

            self.value = self.get_relation()
            time.sleep(.1)

        # self.lcd.clear()
        # self.lcd.putstr("Valor:{}    \nCancelar --  OK".format(self.value))
        self.step_2()

    def step_2(self):

        self.btn1.set_action(self.home)
        self.btn3.set_action(self.process_2)
        self.lcd.clear()
        self.lcd.putstr("Llene y enrase\nCancelar --  OK")

    def process_2(self):

        self.btn1.set_action(no_action)
        self.btn3.set_action(no_action)
        self.lcd.clear()
        self.lcd.putstr("!! PROCESANDO  \n      MATERIAL !!")
        p_peso = int((self.load_cell.get_value(self.config["load_cell"]["samples"],
                                               self.config["load_cell"]["delay"],)[0]) * self.load_cell.get_factor())

        p_relacion = self.get_relation()/self.value * 1024
        temp_v = self.read_vterm()
        temp_b = self.read_bterm()
        offset = self.get_osc_offset()[0]
        auxi = self.config["rf"]["vaso_auxi"]

        medicion = medicion_grano(p_peso,
                                  p_relacion,
                                  temp_v,
                                  temp_b,
                                  offset,
                                  self.current_material.t_coef,
                                  self.current_material.slope,
                                  self.current_material.y0,
                                  self.current_material.c_coef,
                                  self.kalvaso,
                                  self.current_material.hum_rf,
                                  auxi
                                  )
        self.lcd.clear()
        self.lcd.putstr("Humedad :{0:.1f}% \nPH:{1:.2f}".format(medicion[0], medicion[1]))
        self.lcd.move_to(13,1)
        self.lcd.putstr('OK')

        self.btn1.set_action(no_action)
        self.btn3.set_action(self.home)

delver = Delver(lcd, scale)



# APi endpoints+
## Config system
def config_load_cell(method, params):
    if method == 'get':
        return delver.config['load_cell']
    else:
        result = update_config(delver.config['load_cell'], params)

        if result['result'] == 200:
            save_config(delver.config)
            return result
        else:
            return result

def config_rf(method, params):
    if method == 'get':
        return delver.config['rf']
    else:
        result = update_config(delver.config['rf'], params)
        if result['result'] == 200:
            save_config(delver.config)
            return result
        else:
            return result

def config_thermal(method, params):
    if method == 'get':
        return delver.config['thermal']
    else:
        result = update_config(delver.config['thermal'], params)
        if result['result'] == 200:
            save_config(delver.config)
            return result
        else:
            return result

def config_system(method, params):
    if method == 'get':
        return delver.config['system']
    else:
        result = update_config(delver.config['system'], params)
        if result['result'] == 200:
            save_config(delver.config)
            return result
        else:
            return result

## Control system
def control_rf(method, params):
    print(params)
    if method == "post":
        delver.set_osc(params["enosc"], params["midosc"], params["midvaso"])

    return {"result": 200,
            "enosc": bool(delver.enosc.value()),
            "midosc": bool(delver.midosc.value()),
            "midvaso": bool(delver.midvaso.value()),
            }

def control_tare(params=None):
    delver.load_cell.tare(delver.config["load_cell"]["samples"], delver.config["load_cell"]["delay"])
    tara = delver.load_cell.get_offset()*delver.load_cell.get_factor()
    return {"result": 200, "msg": "Tara aplicada", "value": tara}

## Measure system

def measure_rf(params):
    samples = params["samples"] if "samples" in params else delver.config["rf"]["samples"]
    delay = params["delay"] if "delay" in params else delver.config["rf"]["delay"]
    read = delver.read_rf(samples=samples, delay=delay)

    if "raw" in params and params["raw"]:
        value = read[0]
        std_dev = read[1]
    else:
        value = read[2]
        std_dev = read[3]

    return {"result": 200, "value": value, "std_dev": std_dev}

def measure_load_cell(params):
    samples = params["samples"] if "samples" in params else delver.config["load_cell"]["samples"]
    delay = params["delay"] if "delay" in params else delver.config["load_cell"]["delay"]
    read = delver.load_cell.get_value(samples, delay)

    if "raw" in params and params["raw"]:
        value = read[0]
        std_dev = read[1]
    else:
        value = (read[0]-delver.load_cell.get_offset())*delver.load_cell.get_factor()
        std_dev = read[1]*delver.load_cell.get_factor()

    return {"result": 200, "value": value, "std_dev": std_dev}

def measure_thermal(params):
    # print(params)
    if "sensor" in params:
        sensor = params["sensor"]
        # print (sensor)

        if sensor in delver.config["thermal"]:

            samples = params["samples"] if "samples" in params else delver.config["thermal"][sensor]["samples"]
            delay = params["delay"] if "delay" in params else delver.config["thermal"][sensor]["delay"]

            adc = delver.vterm if sensor == "vterm" else delver.bterm
            # print(adc)

            read = delver.read_adc(adc, vref=3.3, n=samples, delay_us=delay)

            if "raw" in params and params["raw"]:
                value = read[0]
                std_dev = read[1]

            else:
                a = delver.config["thermal"][sensor]["coef_a"]
                b = delver.config["thermal"][sensor]["coef_b"]
                # print(a, b)
                value = round(delver.adc_to_temp(read[0], a, b), 1)

                std_dev = round(delver.adc_to_temp(read[0]+read[1], a, b)-value, 1)

            return {"result": 200, "value": value, "std_dev": std_dev}
        else:
            return {"result": 404, "msg": "Sensor {} not found".format(params["sensor"])}
    else:
        return {"result": 400, "msg": "El kewyword sensor no se encontro en los parametros recibidos"}

#Material system

def api_favourite_materials(method, params):
    # print(method, params)
    if method == 'get':

        return {"result": 200, "materials": delver.config['materials']}
    else:
        result = update_config(delver.config, params)
        if result["result"] == 200:
            save_config(delver.config)
        return result


def api_material_add(params):
    try:
        add_material(params)
        return {"result":200, "msg": "El material se acrego correctamente."}
    except Exception as e:
        return{"result": 400, "msg": "No se pudo agregar el material. Error:{}".format(str(e))}

def api_material_get_material(params):
    try:
        material = material_from_code(params['code'])
        m_dict = material.__dict__
        # m_dict["result"] = 200
        return m_dict

    except Exception as e:
        return{"result": 400, "msg": "No se pudo recuperar el material. Error:{}".format(str(e))}

def api_material_delete(params):
    try:
        remove_material(params['code'])
        return {"result": 200, "msg": "El material se borro correctamente."}

    except Exception as e:
        return{"result": 400, "msg": "No se pudo borrar el material. Error:{}".format(str(e))}

# Config system
api.add_command('config/get/load-cell', config_load_cell)
api.add_command('config/post/load-cell', config_load_cell)
api.add_command('config/get/thermal', config_thermal)
api.add_command('config/post/thermal', config_thermal)
api.add_command('config/get/rf', config_rf)
api.add_command('config/post/rf', config_rf)
api.add_command('config/get/system', config_system)
api.add_command('config/post/system', config_system)
# Control system
api.add_command('control/get/rf', control_rf)
api.add_command('control/post/rf', control_rf)
api.add_command('control/tare',  control_tare)
# Measure system
api.add_command('measure/load-cell', measure_load_cell)
api.add_command('measure/thermal', measure_thermal)
api.add_command('measure/rf', measure_rf)
# Material system
api.add_command('materials/get/favourite', api_favourite_materials)
api.add_command('materials/post/favourite', api_favourite_materials)
api.add_command('materials/get', api_material_get_material)
api.add_command('materials/add', api_material_add)
api.add_command('materials/delete', api_material_delete)


def run_in_trhead():
    while True:
        api.read_command()
        time.sleep(.5)
        gc.collect()

mainthread = _thread.start_new_thread(run_in_trhead,())





