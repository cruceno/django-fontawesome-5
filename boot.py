import machine
machine.freq(240000000)
import esp
esp.osdebug(None)
import micropython
micropython.alloc_emergency_exception_buf(100)