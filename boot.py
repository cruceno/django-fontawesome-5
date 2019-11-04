import network
import utime

import esp, esp32
esp.osdebug(None)

import gc
gc.collect()


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


# connect("WiFi_IFIR-INFORMATICA", "infarm412")
# connect("Fibertel WiFi106 2.4GHz", "0043103446")
esp32.wake_on_touch(True)
