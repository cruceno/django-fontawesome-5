import network
import utime
import esp, esp32
from machine import UART
esp.osdebug(None)

def connect(ssid, password, trys=3):

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Connecting to network...')
        sta_if.active(True)
        # TODO: Cambiar wifi aca
        sta_if.connect(ssid, password)
        count = 0
        while not sta_if.isconnected():
            if count == trys:
                break
            else:
                count += 1
            utime.sleep(1)

    print('network config:', sta_if.ifconfig())

esp32.wake_on_touch(True)
