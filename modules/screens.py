from machine import I2C, Pin, PWM, DAC
from esp8266_i2c_lcd import I2cLcd
from pins import ON_LCD, LCD_SDA, LCD_SCL
from math import floor

_MENU_PRINCIPAL = ["ELEGIR MATERIAL", "CONFIGURACION", "PESAR MUESTRA", "DEBUG", "APAGAR"]
_MENU_CONFIGURACION = ["MEDIR BATERIA", "VER TAB.0162", "REPETICIONES", "AJUSTAR HUMEDAD", "LUZ DE FONDO",
                       "CONTRASTE", "REGISTRO", "HORA Y FECHA", "VER REGISTRO"]


class DelverDisplay (I2cLcd):

    def __init__(self,
                 i2c=I2C(scl=Pin(LCD_SCL), sda=Pin(LCD_SDA), freq=400000),
                 address=0x27,
                 rows=2,
                 columns=16,
                 control_pin=ON_LCD,
                 mode=1
                 ):

        if mode == 1:
            self.contrast = DAC(Pin(control_pin, Pin.OUT))
            self.contrast.write(20)
        else:
            self.on_pin = Pin(control_pin, Pin.OUT, value=1)
        self.contrast_index = 2
        super(DelverDisplay, self).__init__(i2c, address, rows, columns)
        self.columns = self.num_columns
        self.rows = self.num_lines

    def align_and_crop_line(self, line, align="left"):
        if len(line) > self.columns:
            #crop
            pass
        elif line == 16:
            return line
        else:
            margin = (16-len(line))/2
            if margin < 1:
                return line+' '*int((margin*2))
            else:
                if align == "center":
                    return ' '*int(floor(margin))+line+' '*(16-len(line)-int(floor(margin)))
                elif align == "left":
                    return line+' '*int(floor(margin)*2)
                elif align == "right":
                    return ' '*int(floor(margin)*2)+line
                else:
                    raise LookupError('align must be "left", "center", or "right". Not: {}'.format(align))

    def home(self,  material):
        line1 = self.align_and_crop_line("ANALIZAR HUMEDAD", "center")
        line2 = self.align_and_crop_line(material, "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def menu(self,menu,  menu_item=0):

        line1 = self.align_and_crop_line(menu[menu_item], "left")
        if menu_item < len(menu)-1:
            line2 = self.align_and_crop_line(menu[menu_item+1], "left")
        else:
            line2 = self.align_and_crop_line(menu[0], "left")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(15,0)
        self.putchar("<")
        self.move_to(0, 1)
        self.putstr(line2)
        return menu_item

    def show_bat(self, value):
        line1 = self.align_and_crop_line("BATERIA", "center")
        line2 = self.align_and_crop_line("{}%".format(value), "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def select_material(self, material, next):
        line1 = self.align_and_crop_line(material, "left")

        if next is None:
            line2 = " "*self.columns
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(15,0)
        self.putchar("<")
        self.move_to(0, 1)
        self.putstr(line2)

    def step_1(self):
        line1 = self.align_and_crop_line("VERIFICAR", "center")
        line2 = self.align_and_crop_line("VASO VACIO", "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def process_1(self):
        line1 = self.align_and_crop_line("MIDIENDO TARA", "center")
        line2 = self.align_and_crop_line("DE BALANZA", "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def step_2(self, material):
        line1 = self.align_and_crop_line(material, "center")
        line2 = self.align_and_crop_line("VUELQUE Y ENRASE", "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def process_2(self):
        line1 = self.align_and_crop_line("PROCESANDO MATERIAL", "center")
        line2 = self.align_and_crop_line(" "*16, "left")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def progress_bar(self, step):
        self.move_to(step, 1)
        self.putchar(">")

    def show_results_1(self, material, hum):
        line1 = self.align_and_crop_line(material, "center")
        line2 = self.align_and_crop_line("HUMEDAD {0:.1f}%".format(hum), "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def show_results_2(self, temp, peso):
        line1 = self.align_and_crop_line("TEMPERATURA {0:.0f} ºC".format(temp), "center")
        line2 = self.align_and_crop_line("PESO {0:.0f}Gr.".format(peso), "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def show_results_3(self, hect):
        line1 = self.align_and_crop_line("P.HECT {0:.2f} Kg/Hl".format(hect), "center")
        line2 = self.align_and_crop_line(" "*16, "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def pesar_muestra_1(self):
        line1 = self.align_and_crop_line("CARGUE MATERIAL", "center")
        line2 = self.align_and_crop_line(" "*16, "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def pesar_muestra_result(self, peso):
        line1 = self.align_and_crop_line("PESO {0:.0f} Gr.".format(peso), "center")
        line2 = self.align_and_crop_line(" "*16, "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def contrast_menu(self):
        line1 = self.align_and_crop_line("CONTRASTE", align="center")
        line2 = self.align_and_crop_line(" - "+"_"*10+" + ", "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)
        self.move_to(self.contrast_index+3, 1)
        self.putchar("x")

    def adjust_contrast(self, increment):
        if 3 <= self.contrast_index+3 + increment or self.contrast_index+3 + increment <= 12:
            self.move_to(self.contrast_index+3, 1)
            self.putchar("_")

            self.contrast_index = self.contrast_index+increment

            self.move_to(self.contrast_index+3, 1)
            self.putchar("x")
            self.contrast.write(100-int(self.contrast_index*10))

        else:
            print (self.contrast_index)
            pass

