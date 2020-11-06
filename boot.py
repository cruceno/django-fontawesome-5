from screens import DelverDisplay, _MENU_CONFIGURACION, _MENU_PRINCIPAL
lcd = DelverDisplay()
lcd.presentation()

import machine
machine.freq(240000000)
import esp
esp.osdebug(None)
import micropython
micropython.alloc_emergency_exception_buf(100)
import gc
rtc = machine.RTC()
# rtc.init((2014, 5, 1, 4, 13, 0, 0, 0))
print(rtc.datetime())
