from pins import *
from machine import I2C, Pin, UART, ADC, reset, deepsleep
import esp32
import utime as time
from uarray import array
import _thread
from button import Button, no_action
from math import log
from statistics import mean, stdev

from serialapi import SerialAPI
from scales import Scales
from config import load_config, update_config, save_config
from materials import material_from_code, add_material, remove_material, make_material_index, get_mat_index
from screens import DelverDisplay, _MENU_CONFIGURACION, _MENU_PRINCIPAL
from delver import DelverBuzz
import uio
import gc
from calculations import correct_temperature, spline_curve_point

index = get_mat_index()

#TODO: Para version de placa final. pasar el pin a 0 y usar para apagar el biestable mandando un 1
rf_mosfet = Pin(ON_RF, Pin.OUT, value=1)

uart = UART(2, 115200)
i2c = I2C(scl=Pin(LCD_SCL), sda=Pin(LCD_SDA), freq=400000)
scale = Scales(d_out=HX711_DT, pd_sck=HX711_SCK)
api = SerialAPI(uart)
lcd = DelverDisplay()

# def go_to_sleep():
    #TODO: Cambiar logica en placa a bateria. Mandar un 1 para apagar biestable.

    # rf_mosfet.off()

    #TODO: No hace falta en placa definitiva el display se apaga al apagarse la fuente

    # lcd.backlight_off()
    # lcd.display_off()
    # deepsleep()


class Delver:
    def __init__(self, lcd, scale, buzzer):
        self.config = load_config()
        self.kalvaso = self.config['rf']['calibration']
        self.lcd = lcd
        self.lcd.set_contrast(self.config['system']['display_contrast'])
        self.lcd.set_max_contrast(self.config['system']['display_contrast_max'])

        self.load_cell = scale
        self.load_cell.set_factor(self.config['load_cell']["calibration_factor"])
        self.buzzer = DelverBuzz(buzzer)

        self.vterm = ADC(Pin(VTERM))  # OSC Pin 3
        self.vterm.atten(ADC.ATTN_11DB)

        self.bterm = ADC(Pin(BTERM))  # OSC Pin 9
        self.bterm.atten(ADC.ATTN_11DB)

        self.rfval = ADC(Pin(RFVAL))  # OSC Pin 10
        self.rfval.atten(ADC.ATTN_11DB)

        self.midbat = ADC(Pin(MID_BAT))
        self.midbat.atten(ADC.ATTN_11DB)

        # DIGITAL OUTPUTS (value 0 is 3.3v on value 1 is 0v)
        self.enosc = Pin(ENOSC, Pin.OUT, value=1)  # OSC Pin 2
        self.midvaso = Pin(MIDVASO, Pin.OUT, value=1)  # OSC Pin 6
        self.midosc = Pin(MIDOSC, Pin.OUT, value=1)  # OSC Pin 8

        self.btn1 = Button(BTN1, irq=Pin.IRQ_RISING,mode=Pin.IN, pull = Pin.PULL_DOWN,
                           debounce_time=self.config["system"]["button_debounce_time"], )

        self.btn2 = Button(BTN2, irq=Pin.IRQ_RISING, mode=Pin.IN, pull = Pin.PULL_DOWN,
                           debounce_time=self.config["system"]["button_debounce_time"])

        self.btn3 = Button(BTN3, irq=Pin.IRQ_RISING, mode=Pin.IN, pull = Pin.PULL_DOWN,
                           debounce_time=self.config["system"]["button_debounce_time"])

        self._menu_actions = {
            0: self.select_favourite_material,
            1: self.config_menu,
            2: self.pesar_muestra,
            3: self.debug_page,
            4: self.shut_down
        }

        self._config_actions = {
            0: self.show_bat_status,
            1: self.show_tables,
            2: self.set_repeat,
            3: self.fix_humidity,
            4: self.set_backlight_time,
            5: self.fix_contrast,
            6: self.register,
            7: self.set_time,
            8: no_action

        }

        self.value = 0
        self.func = 0
        self._busy = False
        self._menu_index = 0
        self.stop = True
        self.LCD_STATE = True
        self.current_material = self.config["system"]["last_used_material"]
        self.previous_material = "000"
        self.fav_index = 0
        self.last_action = time.time()

        self.buzzer.ok()
        self._thread = None

        self.home()

    def go_to_sleep(self):
        #TODO: USar esta funcion en lugar de la definida arriba ?
        self.lcd_on_off()
        save_config(self.config)
        # self.btn3.pin.init(Pin.IN, Pin.PULL_DOWN)
        deepsleep()

    def is_busy(self):
        return self._busy

    def reload_config(self):
        self.config = load_config()
        self.load_cell.set_factor(self.config['load_cell']["calibration_factor"])
        self.kalvaso = self.config['rf']['calibration']

    def read_adc(self, adc, n=100, delay_us=10, raw=False):
        # rf_mosfet.on()
        values = []
        for i in range(0, n):
            read = adc.read()
            values.append(read)
            acum = (read - values[i-1])/n + values[i-1]
            values[i] = acum
            time.sleep_us(delay_us)

        prom = mean(values)
        deviation = stdev(values, prom)

        if raw:
            return prom, deviation

        prom_v = round(mean([self.config['adc_calibration']['k'] +
                             self.config['adc_calibration']['a'] * v +
                             self.config['adc_calibration']['b'] * v ** 2 +
                             self.config['adc_calibration']['c'] * v ** 3 for v in values]), 3)

        deviation_v = round(stdev([self.config['adc_calibration']['k'] +
                                   self.config['adc_calibration']['a'] * v +
                                   self.config['adc_calibration']['b'] * v ** 2 +
                                   self.config['adc_calibration']['c'] * v ** 3 for v in values], prom_v), 3)

        return int(prom), int(deviation), prom_v, deviation_v

    def lcd_on_off(self):
        if self.LCD_STATE:
            self.buzzer.fail()
            self.lcd.backlight_off()
            self.lcd.display_off()
            self.LCD_STATE = False
        else:
            self.lcd.backlight_on()
            self.lcd.display_on()
            self.home()
            self.buzzer.ok()
            self.LCD_STATE = True
            self.lcd.hide_cursor(True)

    # RF functions
    def read_rf(self, samples=None, delay=None):
        # rf_mosfet.on()

        samples = self.config["rf"]["samples"] if samples is None else samples
        delay = self.config["rf"]["delay"] if delay is None else delay

        read = self.read_adc(self.rfval, n=samples, delay_us=delay)

        while read[1] > 1:
            read = self.read_adc(self.rfval, n=samples, delay_us=delay)

        # rf_mosfet.off()
        return read

    def set_osc(self, e, o, v):
        self.enosc.value(e)  # Deshabilita enosc
        self.midosc.value(o)  # Deshabilita midosc
        self.midvaso.value(v) # Deshabilita midvaso
        time.sleep_us(100)

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

    ## Temperature functions
    def read_temperature(self, sensor,
                         n=None,
                         delay_us=None,
                         raw=False):

        adc = self.read_adc(self.vterm if sensor == 'vterm' else self.bterm,
                            n=self.config['thermal'][sensor]['samples'] if n is None else n,
                            delay_us=self.config['thermal'][sensor]['delay'] if delay_us is None else delay_us,
                            raw=True)
        if raw:
            return adc

        a = self.config['thermal'][sensor]['coef_a']
        b = self.config['thermal'][sensor]['coef_b']

        value = log(adc[0]/a)/b if adc[0] != 0 else 0
        std_dev = (log((adc[0]+adc[1])/a)/b if adc[0]+adc[1] != 0 else 0) - value

        return round(value, 1), round(std_dev, 1)

    ## Display pages
    def toggle_func(self):
        self.last_action = time.time()
        self.buzzer.beep()

        if self.func == 0:
            self.func = 1  # Funcion medir oscilador

        elif self.func == 1:
            self.func = 2  # Funcion medir vaso

        elif self.func == 2:
            self.func = 3

        elif self.func == 3:
            self.func = 4

        elif self.func == 4:
            self.func = 5

        elif self.func == 5:
            self.func = 0

    def debug_thread(self):

        self.lcd.clear()
        self.lcd.putstr("RF{}:     VT:    P:       BT:    ".format(self.func))
        rf = 0
        vt = 0
        bt = 0
        lc = 0
        bat = 0.0

        while not self.stop:
            self.lcd.move_to(2, 0)
            self.lcd.putstr(str(self.func))
            self.lcd.move_to(4, 0)
            if self.func == 5:
                # Mdicion de bateria Volts y Cuentas
                bat = self.read_adc(self.midbat)[2]*self.config['adc_calibration']['resistor_divisor']
                bat = "{0:.2f}".format(bat)
                self.lcd.putstr(bat+' ' if len(bat) == 4 else bat+' '*(5-len(bat)))

            else:
                rf = str(rf)
                self.lcd.putstr(rf+' ' if len(rf) == 4 else rf+' '*(5-len(rf)))

            # Actualiza display valor de Vterm
            self.lcd.move_to(12, 0)
            vt = str(vt)
            self.lcd.putstr(vt if len(vt) == 4 else vt+' '*(4-len(vt)))

            # Actualiza display. Peso o cuentas de bateria   o referencia de oscilador.
            self.lcd.move_to(3, 1)
            if self.func == 4:
                adj = 2.25 - (self.read_temperature("bterm")[0]-22)*7.9/1000
                adj = "{0:.3f}".format(adj)
                self.lcd.putstr(adj if len(adj) == 5 else adj+' '*(5-len(adj)))
            elif self.func == 5:
                bat = self.read_adc(self.midbat)[0]
                bat = str(bat)
                self.lcd.putstr(bat+' ' if len(bat) == 4 else bat+' '*(5-len(bat)))
            else:
                lc = str(lc)
                self.lcd.putstr(lc if len(lc) == 5 else lc+' '*(5-len(lc)))

            # Actualiza display valor de Bterm
            self.lcd.move_to(12,  1)
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

            vt = self.read_temperature(sensor="vterm")[0]
            bt = self.read_temperature(sensor="bterm")[0]
            lc = int((self.load_cell.get_value(samples=self.config["load_cell"]["samples"],
                                               delay=self.config["load_cell"]["delay"])[0]) * self.load_cell.get_factor())

            time.sleep_ms(100)
        self.home()

    def stop_debug(self):
        self.stop = True

    def debug_page(self):
        self.buzzer.beep()
        self.stop = False
        self.set_off_osc()
        self.func = 0
        self.btn1.set_action(self.toggle_func)

        self.btn3.set_action(self.stop_debug)
        self.btn2.set_action(self.load_cell.tare, (self.config["load_cell"]["samples"],
                                                 self.config["load_cell"]["delay"])
                             )
        self._thread = _thread.start_new_thread(self.debug_thread, ())
        self._busy = True

    def shut_down(self):
        save_config(self.config)
        self.btn3.pin.init(Pin.IN, Pin.PULL_DOWN)
        self.go_to_sleep()

    def home(self):
        self.stop = True
        self._busy = False

        if self._thread is not None:
            while self._thread.isRunning():
                continue

        self.buzzer.beep()
        self.fav_index = 0

        self.current_material = index.splitlines()[int(self.config["system"]["last_used_material"])].split('\t')[0]
        material = index.splitlines()[int(self.config["system"]["last_used_material"])].split('\t')[1]

        self.btn1.set_action(self.menu, (0,))
        self.btn2.set_action(self.go_to_sleep, params=None)
        self.btn3.set_action(self.step_1, params=None)

        self.set_off_osc()

        try:
            # Se utiliza rl try para evitar error de profundidad de recursion al
            # volver de otra pantalla
            self.lcd.home(material)
        except:
            self.lcd.home(material)

        self.last_action = time.time()

    def menu(self, index=0):
        self._menu_index = index
        self.lcd.menu(_MENU_PRINCIPAL, self._menu_index)
        self.buzzer.beep()

        if index < len(_MENU_PRINCIPAL)-1:
            print(index, len(_MENU_PRINCIPAL))
            self.btn1.set_action(self.menu, (index+1,))
        else:
            print("else", index, len(_MENU_PRINCIPAL))
            self.btn1.set_action(self.menu, (0,))
        self.btn2.set_action(self.home)
        self.btn3.set_action(self._menu_actions[index])
        self.last_action = time.time()

    def config_menu(self, index=0):
        self._menu_index = index
        if index < len(_MENU_CONFIGURACION)-2:
            # print(index, len(_MENU_CONFIGURACION))
            self.btn1.set_action(self.config_menu, (index+1,))
            self.lcd.menu(_MENU_CONFIGURACION, self._menu_index)

        elif index <= len(_MENU_CONFIGURACION)-1:
            if index < len(_MENU_CONFIGURACION)-1:
                self.btn1.set_action(self.config_menu, (index+1,))
            else:
                self.btn1.set_action(self.config_menu, (0,))

            self.lcd.menu(_MENU_CONFIGURACION, self._menu_index, self.config["system"]["cic"])

        else:
            # print("else", index, len(_MENU_CONFIGURACION))
            self.btn1.set_action(self.config_menu, (0,))

        self.btn2.set_action(self.menu, (0,))
        self.buzzer.beep()
        self.btn3.set_action(self._config_actions[index])
        self.last_action = time.time()

    def pesar_muestra(self):
        self.lcd.step_1()
        self.buzzer.beep()
        self.btn2.set_action(self.menu)
        self.btn1.clear_action()
        self.btn3.set_action(self.pesar_muestra_tara)
        self.last_action = time.time()

    def pesar_muestra_tara(self):
        self.lcd.process_1()
        self.load_cell.tare(self.config["load_cell"]["samples"], self.config["load_cell"]["delay"])
        self.buzzer.beep()
        self.btn2.set_action(self.home)
        self.lcd.pesar_muestra_1()
        self.stop = False
        self.btn1.clear_action()
        self._thread = _thread.start_new_thread(self.weigth_monitor_thread, (1,))
        self.last_action = time.time()

    def show_bat_status(self):
        self.btn1.clear_action()
        self.btn2.clear_action()
        self.btn3.set_action(self.home)
        bat = self.read_adc(self.midbat)[2]
        min = self.config["system"]["min_battery_value"]
        max = self.config["system"]["max_battery_value"]
        value = (bat-min)*100/(max-min)
        self.lcd.show_bat(value)
        self.last_action = time.time()

    def show_tables(self):
        #TODO: FUNCION MOSTRAR TABLA
        pass

    def set_repeat(self):
        #TODO: FUNCIONALIDAD DE REPETICIONES
        pass

    def fix_humidity(self):
        #TODO: FUNCION DE AJUSTE DE HUMEDAD POR MATERIAL
        pass

    def set_backlight_time(self, value=0):

        if value == 99:
            save_config(self.config)
            self.home()

        elif value == 0:
            self.btn1.set_action(self.set_backlight_time, (-10,))
            self.btn2.set_action(self.set_backlight_time, (10,))
            self.btn3.set_action(self.set_backlight_time, (99,))
            self.lcd.backlight_time(self.config["system"]["backlight_off"])
            self.buzzer.beep()

        else:
            if 0 < self.config["system"]["backlight_off"] < 100:
                self.config["system"]["backlight_off"] += value
            else:
                if self.config["system"]["backlight_off"] == 0 < value:
                    self.config["system"]["backlight_off"] += value
                elif self.config["system"]["backlight_off"] >= 100 and value < 0:
                    self.config["system"]["backlight_off"] += value
            self.lcd.backlight_time(self.config["system"]["backlight_off"])
            self.buzzer.beep()
        self.last_action = time.time()

    def fix_contrast(self, increment=0):
        self.lcd.contrast_menu()
        self.buzzer.beep()
        # self.lcd.contrast_index = self.lcd.contrast_index+increment
        self.btn1.set_action(self.increment_contrast, (-1,))
        self.btn2.set_action(self.increment_contrast, (1,))
        self.btn3.set_action(self.menu)
        self.last_action = time.time()

    def increment_contrast(self, increment):
        self.buzzer.beep()
        if 2 <= self.lcd.contrast_index+2 + increment and self.lcd.contrast_index+2 + increment <= 13:
            print("3<={}+3+{} and {}+3+{} <=12".format(self.lcd.contrast_index,
                                                       increment,
                                                       self.lcd.contrast_index,
                                                       increment)
                   )
            self.lcd.adjust_contrast(increment)
        else:
            pass
        self.last_action = time.time()

    def register(self):
        #TODO: FUNCION DE GRABAR REGISTROS
        pass

    def set_time(self, mode=0,):
        #TODO: AJUSTE DE FECHA Y HORA
        self.buzzer.beep()
        if mode == 0:
            self.lcd.show_date_time(rtc.datetime())
            self.btn1.clear_action()
            self.btn2.clear_action()
            self.btn3.set_action(self.config_menu)

        self.last_action = time.time()


    def select_favourite_material(self):
        self.buzzer.beep()
        self.btn1.set_action(self.select_favourite_material)
        self.btn2.set_action(self.home)
        # self.lcd.clear()
        # self.lcd.putstr('! Buscando        material !')
        if self.fav_index <= 9:
            self.current_material = index.splitlines()[int(self.config["materials"][self.fav_index])].split('\t')[0]
            name = index.splitlines()[int(self.config["materials"][self.fav_index])].split('\t')[1]
            self.fav_index = self.fav_index + 1
            name = name[0:14] if len(name) > 15 else name
            self.lcd.clear()
            screen = name+'\n'+"Next  Back  Ok"
            self.lcd.putstr(screen)
            self.btn3.set_action(self.step_1)

        else:
            self.lcd.clear()
            self.btn3.set_action(self.select_material)
            self.current_material = "000"
            self.lcd.putstr("  Ver  todos \n      Back    Ok")
        self.last_action = time.time()

    def select_material(self):
        self.buzzer.beep()
        self.fav_index = 0
        # self.lcd.clear()

        if not self.current_material:
            self.current_material = index.splitlines()[1].split('\t')[0]
        else:
            i = int(self.current_material)+1
            self.current_material = index.splitlines()[i].split('\t')[0]

        self.btn1.set_action(self.select_material)

        self.btn2.set_action(self.select_favourite_material)
        self.btn3.set_action(self.step_1)

        name = index.splitlines()[int(self.current_material)].split('\t')[1]
        self.lcd.move_to(0, 0)
        name = name[0:14] if len(name) > 15 else name+" "*(15-len(name))

        self.lcd.putstr(name+'\n'+"{}   {}   Ok".format("Next" if int(self.current_material) < len(index.splitlines())-1 else " "*4,
                                                        "Back" if int(self.current_material) > 1 else " "*4))
        self.last_action = time.time()

    def step_1(self):
        self.buzzer.beep()
        self.stop = True
        self.btn1.clear_action()
        self.btn2.set_action(self.home)
        self.btn3.set_action(self.process_1)
        self.lcd.step_1()
        self.last_action = time.time()

    def process_1(self):
        self._busy=True
        self.buzzer.beep()
        self.btn1.clear_action()
        self.btn3.clear_action()
        self.lcd.process_1()
        self.value = 0
        self.load_cell.tare(self.config["load_cell"]["samples"], self.config["load_cell"]["delay"])
        while self.value == 0:
            self.value = self.get_relation()
            time.sleep_ms(100)

        self.buzzer.beep()
        self.btn1.set_action(self.home)
        self.btn3.set_action(self.process_2)
        material = index.splitlines()[int(self.current_material)].split('\t')[1]

        self.lcd.step_2(material)
        self.stop = False
        # self._thread = _thread.start_new_thread(self.weigth_monitor_thread, (0,))

    def weigth_monitor_thread(self, mode=0):
        self._busy = True
        while not self.stop:
            p = self.load_cell.get_value()
            p_neto = int((p[0] * self.load_cell.get_factor()))

            self.lcd.pesar_muestra_result(p_neto)

            if mode == 0:
                self.lcd.move_to(13, 1)
                self.lcd.putstr("{}".format("OK") if p_neto > self.config["load_cell"]["min_load_to_work"] else "   ")

            if p_neto > 0:
                if mode == 0:
                    self.btn3.set_action(self.process_2)
                else:
                    self.btn3.set_action(self.home)
            else:
                if mode == 0:
                    self.btn3.clear_action()
                else:
                    self.btn3.set_action(self.home)
            time.sleep_ms(300)

    def process_2(self, step=0, medicion=None):
        self.buzzer.beep()
        if step == 0:
            # update_config(self.config, {"last_used_material": self.current_material,
            #                             "cic": self.config["system"]["cic"] + 1})
            self.stop = True
            if self._thread is not None:
                while self._thread.isRunning():
                    continue

            self.btn1.clear_action()
            self.btn2.set_action(self.home)
            self.btn3.set_action(self.home)
            #TODO: pasar mensaje a archivo de pantallas
            line1 = self.lcd.align_and_crop_line("PROCESANDO", "center")
            line2 = self.lcd.align_and_crop_line(" "*16, "left")
            self.lcd.move_to(0, 0)
            self.lcd.putstr(line1)
            self.lcd.move_to(0, 1)
            self.lcd.putstr(line2)
            self.lcd.progress_bar(1)
            p_peso = int((self.load_cell.get_value(self.config["load_cell"]["samples"],
                                                   self.config["load_cell"]["delay"],)[0]) * self.load_cell.get_factor())
            self.lcd.progress_bar(2)
            if p_peso >= self.config["load_cell"]["min_load_to_work"]:
                self.lcd.progress_bar(3)
                p_relacion = self.get_relation()/self.value * 1024
                self.lcd.progress_bar(4)
                temp_v = self.read_temperature("vterm")[0]
                self.lcd.progress_bar(5)
                temp_b = self.read_temperature("bterm")[0]
                self.lcd.progress_bar(6)
                offset = self.get_osc_offset()[0]
                self.lcd.progress_bar(7)
                auxi = self.config["rf"]["vaso_auxi"]
                material = material_from_code(self.current_material)
                self.lcd.progress_bar(8)

                results = self.medicion_grano(p_peso,
                                           p_relacion,
                                           temp_v,
                                           temp_b,
                                           offset,
                                           material.t_coef,
                                           material.slope,
                                           material.y0,
                                           material.c_coef,
                                           self.kalvaso,
                                           material.hum_rf,
                                           auxi
                                           )
                self.buzzer.ok()
                self.lcd.progress_bar(15)
                print(material.name, results[0])
                self.config["system"]["last_used_material"] = self.current_material

                self.lcd.show_results_1(material.name, results[0])
                self.btn3.set_action(self.process_2, (1, results))
            # self.lcd.putstr("Humedad :{0:.1f}% \nPH:{1:.2f}".format(medicion[0], medicion[1]))
            # self.lcd.move_to(13, 1)
            # self.lcd.putstr('OK')
            # print(gc.mem_free())
                return

            else:
                self.buzzer.fail()
                self.step_2()
                return

        elif step == 1:
            print(medicion)
            self.lcd.show_results_2(medicion[3], medicion[2])
            self.btn3.set_action(self.process_2, (2, medicion))

        elif step == 2:
            self.lcd.show_results_3(medicion[1])
            self.btn3.set_action(self.home)

    def medicion_grano(self, p_peso, p_relacion, temp_v, temp_b, offset, m_t_coef, m_slope, m_y0, m_c_coef,
                       kalvaso, m_curve, auxi):
        # print(p_peso, p_relacion, offset)
        self.lcd.progress_bar(9)
        value = correct_temperature(p_relacion, temp_b, offset)
        # api.write_response("Relacion corregida por temperatura: {0:.2f}\n".format(value))
        x = range(0, 1025, 64)
        # y = [0,	29,	60,	98,	147, 178, 164, 127, 115, 97, 57, 27, 7, -2,	-4,	-2,	0]
        # print(kalvaso)
        # print(gc.mem_free())
        self.lcd.progress_bar(10)
        correcion = spline_curve_point(value, x, kalvaso, 64, 0.5)
        # print(gc.mem_free())


        # api.write_response("Correccion por patron: {0:.2f}\n".format(correcion))
        relacorr = value + correcion
        # api.write_response("Relacion corregida por patron: {0:.2f}\n".format(relacorr))
        relacion = (1024-relacorr-m_y0*2)*4*(m_slope/auxi)/p_peso
        # api.write_response("Relacion corregida por peso hectrolitrico: {0:.2f}\n".format(relacion))
        x = range(32, 1024, 32)
        # y =[0, 0, 26, 16, 16,16,16,15,16,16,16,16,17,16,17,17,16,17,17,16,17,17,16,17,17,16,17,17,16,255,0,0]
        # print(m_curve)
        h_acum = array('i', [])
        self.lcd.progress_bar(11)
        for h in m_curve:
            if len(h_acum) == 0:
                h_acum.append(h)
            else:
                h_acum.append(h + h_acum[len(h_acum)-1])

        # print(h_acum)
        self.lcd.progress_bar(12)
        humedad = spline_curve_point(relacion, x, h_acum, 200, 0.5)

        # api.write_response("Humedad desde tabla material: {0:.1f}\n".format(humedad))
        self.lcd.progress_bar(13)
        h_final = humedad-(m_t_coef-80)/64*(temp_v-22)
        # api.write_response("Humedad corregida por temperatura: {0:.2f}\n".format(h_final))
        # api.write_response("Humedad: {0:.1f}\n".format(h_final/10))
        # api.write_response("Peso Hectolitrico: {0:.2f}\n".format(p_peso*m_c_coef*auxi/640))
        self.config["system"]["cic"] = self.config["system"]["cic"] + 1
        save_config(self.config)
        self.lcd.progress_bar(14)

        return round(h_final/10, 1), p_peso*m_c_coef*auxi/640, p_peso, temp_v


delver = Delver(lcd, scale, BUZZER)

# APi endpoints+
#TODO: Los mensajes del api tambien tienen que estar traducidos ? o se traducen a nivel software desktop ?

# Config system
def config_load_cell(method, params):
    if method == 'get':
        return delver.config['load_cell']
    else:
        result = update_config(delver.config['load_cell'], params)

        if result['result'] == 200:
            save_config(delver.config)
            delver.reload_config()
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
            delver.reload_config()
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
            delver.reload_config()
            return result
        else:
            return result

def config_adc_calibration(method, params):
    if method == 'get':
        return delver.config['adc_calibration']
    else:
        result = update_config(delver.config['adc_calibration'], params)
        if result['result'] == 200:
            save_config(delver.config)
            delver.reload_config()
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
            delver.reload_config()
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

def control_reset (params = None):
    reset()
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
        value = read[0]*delver.load_cell.get_factor()
        std_dev = read[1]*delver.load_cell.get_factor()

    return {"result": 200, "value": value, "std_dev": std_dev}

def measure_thermal(params):
    # print(params)
    if "sensor" in params:
        sensor = params["sensor"]
        # print (sensor)

        if sensor in delver.config["thermal"]:
            samples = params["samples"] if "samples" in params else None
            delay = params["delay"] if "delay" in params else None
            raw = True if "raw" in params and params["raw"] else False
            read = delver.read_temperature(sensor, samples, delay, raw)
            value = read[0]
            std_dev = read[1]

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
            delver.reload_config()
        return result


def api_material_add(params):
    try:
        add_material(params)
        return {"result": 200, "msg": "El material se acrego correctamente."}
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

def api_battery_check(params=None):
    min = delver.config["system"]["min_battery_value"]
    max = delver.config["system"]["max_battery_value"]
    bat = delver.read_adc(delver.midbat)[2]*delver.config['adc_calibration']['resistor_divisor']
    if bat < min:
        # Battery is low pleas replace
        return {"result": 200, "battery": 0.0}

    elif min < bat < max:
        value = bat - min
        bat_percent = value * 100 / (max-min)
        return {"result": 200, "battery": round(bat_percent, 1)}
    else:
        return {"result": 200, "battery": 100.0}

# Config system
api.add_command('config/get/load-cell', config_load_cell)
api.add_command('config/post/load-cell', config_load_cell)
api.add_command('config/get/thermal', config_thermal)
api.add_command('config/post/thermal', config_thermal)
api.add_command('config/get/adc', config_adc_calibration)
api.add_command('config/post/adc', config_adc_calibration)
api.add_command('config/get/rf', config_rf)
api.add_command('config/post/rf', config_rf)
api.add_command('config/get/system', config_system)
api.add_command('config/post/system', config_system)
# Control system
api.add_command('control/get/rf', control_rf)
api.add_command('control/post/rf', control_rf)
api.add_command('control/tare',  control_tare)
api.add_command('control/reset', control_reset)

# Measure system
api.add_command('measure/load-cell', measure_load_cell)
api.add_command('measure/thermal', measure_thermal)
api.add_command('measure/rf', measure_rf)
api.add_command('measure/battery-check', api_battery_check)

# Material system
api.add_command('materials/get/favourite', api_favourite_materials)
api.add_command('materials/post/favourite', api_favourite_materials)
api.add_command('materials/get', api_material_get_material)
api.add_command('materials/add', api_material_add)
api.add_command('materials/delete', api_material_delete)

def run_in_trhead():

    while True:
        if (    delver.config["system"]["backlight_off"]> 0 and
                time.time() - delver.last_action > delver.config["system"]["backlight_off"]) \
                and (delver.is_busy() is False):

            delver.lcd.backlight_off()

        else:
            delver.lcd.backlight_on()

        if time.time() - delver.last_action > delver.config["system"]["time_to_off"] and delver.is_busy() is False:
            save_config(delver.config)
            # delver.btn3.pin.init(Pin.IN, Pin.PULL_DOWN)
            # delver.btn3.pin.pull(Pin.PULL_DOWN)
            delver.go_to_sleep()

        api.read_command()
        time.sleep_ms(500)
        gc.collect()


mainthread = _thread.start_new_thread(run_in_trhead,())
#level parameter can be: esp32.WAKEUP_ANY_HIGH or esp32.WAKEUP_ALL_LOW
# esp32.wake_on_ext0(pin = wake1, level = esp32.WAKEUP_ANY_HIGH)
esp32.wake_on_ext1(pins=(Pin(BTN3),), level=esp32.WAKEUP_ANY_HIGH)





