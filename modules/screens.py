from machine import I2C, Pin, PWM, DAC
from esp8266_i2c_lcd import I2cLcd
from pins import CONTRAST, LCD_SDA, LCD_SCL
from math import floor

#TODO: PERMITIR TRADUCCIION DE MENSAJES
#TODO: TRADUCCION EN EQUIPO O POR API

_MENU_PRINCIPAL = ["ELEGIR MATERIAL", "CONFIGURACION", "PESAR MUESTRA", "DEBUG", "APAGAR"]
_MENU_CONFIGURACION = ["MEDIR BATERIA", "VER TAB.0162", "REPETICIONES", "AJUSTAR HUMEDAD", "LUZ DE FONDO",
                       "CONTRASTE", "REGISTRO", "FECHA Y HORA", "CIC"]


class DelverDisplay (I2cLcd):

    def __init__(self,
                 i2c=I2C(scl=Pin(LCD_SCL), sda=Pin(LCD_SDA), freq=400000),
                 address=0x27,
                 rows=2,
                 columns=16,
                 #TODO: Cambiar Nombre al pin para que refleje su funcion
                 contrast_pin=CONTRAST,
                 contrast_value=60,
                 contrast_max =0
                 ):

        self.contrast = DAC(Pin(contrast_pin, Pin.OUT))
        self.max_contrast = contrast_max
        self.min_contrast = self.max_contrast + 120
        self.contrast.write(self.max_contrast + contrast_value)
        self.contrast_index = int((self.min_contrast-self.max_contrast+contrast_value)/10)

        super(DelverDisplay, self).__init__(i2c, address, rows, columns)
        self.columns = self.num_columns
        self.rows = self.num_lines

    def putchar(self, char):
        """Writes the indicated character to the LCD at the current cursor
        position, and advances the cursor by one position.
        """
        if char != '\n':
            self.hal_write_data(ord(char))
            self.cursor_x += 1
        if self.cursor_x >= self.num_columns or char == '\n':
            self.cursor_x = 0
            self.cursor_y += 1
            if self.cursor_y >= self.num_lines:
                self.cursor_y = 0
            addr = self.cursor_x & 0x3f
            if self.cursor_y & 1:
                addr += 0x40    # Lines 1 & 3 add 0x40
            if self.cursor_y & 2:
                addr += 0x14    # Lines 2 & 3 add 0x14
            self.hal_write_command(self.LCD_DDRAM | addr)

    def align_and_crop_line(self, line, align="left"):
        if len(line) > self.columns:
            #crop
            pass
        elif line == 16:
            return line
        else:
            margin = (16-len(line))/2
            if margin < 1:
                return line
            else:
                if align == "center":
                    return ' '*int(floor(margin))+line+' '*(16-len(line)-int(floor(margin)))
                elif align == "left":
                    return line+' '*(16-len(line))
                elif align == "right":
                    return ' '*int(floor(margin)*2)+line
                else:
                    raise LookupError('align must be "left", "center", or "right". Not: {}'.format(align))

    def presentation(self):
        line1 = self.align_and_crop_line("HIGROMETRO", "center")
        line2 = self.align_and_crop_line("DELVER HD1021", "center")
        self.move_to(0, 0)
        self.putstr(line1)
        # self.move_to(0, 1)
        self.putstr(line2)

    def home(self,  material):
        line1 = self.align_and_crop_line("ANALIZAR HUMEDAD", "center")
        line2 = self.align_and_crop_line(material, "center")
        self.move_to(0, 0)
        self.putstr(line1)
        # self.move_to(0, 1)
        self.putstr(line2)

    def usb_mode(self):

        line1 = self.align_and_crop_line("MODO USB", "center")
        line2 = self.align_and_crop_line("HABILITADO", "center")

        self.move_to(0, 0)
        self.putstr(line1)
        # self.move_to(0, 1)
        self.putstr(line2)

    def menu(self, menu,  menu_item=0, cic=None):
        if cic is not None and menu_item == len(menu)-1:
            cic_str = "{}: {}".format(menu[menu_item], cic)
            line1 = self.align_and_crop_line(cic_str, "left")
        else:
            line1 = self.align_and_crop_line(menu[menu_item], "left")
        if menu_item < len(menu)-1:
            if menu_item == len(menu)-2 and cic is not None:
                cic_str = "{}: {}".format(menu[menu_item+1], cic)
                line2 = self.align_and_crop_line(cic_str, "left")
            else:
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

    def shut_down_in(self, value):
        line1 = self.align_and_crop_line("APAGADO EN", "center")
        line2 = self.align_and_crop_line("{} Seg.".format(value), "center")
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

    def tare_error(self):
        line1 = self.align_and_crop_line("ERROR", "center")
        line2 = self.align_and_crop_line("TARA INCORRECTA", "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def add_material(self, material):
        line1 = self.align_and_crop_line(material, "center")
        line2 = self.align_and_crop_line("FALTA GRANO", "center")
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
        print("Estoy en 2")
        print(temp, peso)
        try:
            line1 = self.align_and_crop_line("TEMPERATURA {0:.0f}C".format(temp), "center")
            print(line1)
            line2 = self.align_and_crop_line("PESO {0:.0f} Gr.".format(peso), "center")
            print(line2)
            self.move_to(0, 0)
            self.putstr(line1)
            self.move_to(0, 1)
            self.putstr(line2)
        except Exception as e:
            print("Falle", temp, peso, str(e))

    def show_results_3(self, hect):
        line1 = self.align_and_crop_line("P.HECTOLITRICO" , "center")
        line2 = self.align_and_crop_line("{0:.2f} Kg/Hl".format(hect), "center")
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
        line2 = self.align_and_crop_line("PESO {0:.0f} Gr.".format(peso), "center")
        # line2 = self.align_and_crop_line(" "*16, "center")
        # self.move_to(0, 0)
        # self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def contrast_menu(self):
        line1 = self.align_and_crop_line("CONTRASTE", align="center")
        line2 = self.align_and_crop_line("- "+"_"*12+" +", "center")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)
        self.move_to(self.contrast_index+2, 1)
        self.putchar("x")

    def backlight_time(self, value):
        line1 = self.align_and_crop_line("LUZ DE FONDO", "center")
        if 0 < value < 100:
            line2 = self.align_and_crop_line("{} Seg.".format(value), "center" )
        elif 0 >= value:
            line2 = self.align_and_crop_line("APAGADO".format(value), "center" )
        elif value >= 100:
            line2 = self.align_and_crop_line("SIEMPRE", "center" )


        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

    def adjust_contrast(self, increment):

        if 2 <= self.contrast_index+2 + increment or self.contrast_index+2 + increment <= 13:
            self.move_to(self.contrast_index+2, 1)
            self.putchar("_")

            self.contrast_index = self.contrast_index+increment

            self.move_to(self.contrast_index+2, 1)
            self.putchar("x")
            print(self.min_contrast-int(self.contrast_index*10))
            self.contrast.write(self.min_contrast-int(self.contrast_index*10))

        else:
            pass

    def set_contrast(self, value):
        if self.min_contrast >= value >= self.max_contrast:
            self.contrast.write(value)
            self.contrast_index = int(value/10)
        else:
            print("Fuera de limites")

    def set_max_contrast(self, value):
        self.max_contrast = value


    def show_date_time(self, datetime):
        line1 = self.align_and_crop_line("{:02d}/{:02d}/{} {:02d}:{:02d}".format(datetime[2],
                                                                                 datetime[1],
                                                                                 datetime[0],
                                                                                 datetime[4],
                                                                                 datetime[5],
                                                                                )
                                        )
        line2 = self.align_and_crop_line("")
        self.move_to(0, 0)
        self.putstr(line1)
        self.move_to(0, 1)
        self.putstr(line2)

