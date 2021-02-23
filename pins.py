from micropython import const
# Pines de placa RF
ENOSC = const(14)
MIDOSC = const(25)
MIDVASO = const(33)

BTERM = const(34)
VTERM = const(35)
RFVAL = const(36)

# Buttons
BTN1 = const(5)
BTN2 = const(18)
BTN3 = const(15)

# Pines UART usado por RELP Micropython
PROG_TX = const(1)
PROG_RX = const(3)


# Pines para UART API
API_RX = const(17)
API_TX = const(16)

# Pines de comunicacion con impresora TTL
PRINT_RX = const(13)
PRINT_TX = const(12)

# Pines de salida para control on/off de perifericos
ON_RF = const(2) # Optoacoplador / mosfet para desenergizar la placa RF
ON_LCD = const(26) # Optoacoplador / mosfet para desenergizar el LCD

# Pines i2c para control de display
LCD_SDA = const(19)
LCD_SCL = const(21)

# Pines para servo y boton de volcado automatico de cereal
SERVO = const(0)
BTN_VOLCADO = const(4) # Entrada boton de volcado.

# Pines para comunicacion con celda decarga
HX711_SCK = const(23)
HX711_DT = const(22)

# MID_BAT = 0 # Medicion de bateria a traves de divisor de tension
MID_BAT = const(32) # Medicion de bateria
BUZZER = const(27) #

