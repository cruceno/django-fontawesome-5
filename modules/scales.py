from hx711 import HX711
from utime import sleep_us
from statistics import mean, stdev


class TareError(Exception):
    def __ini__(self):
        self.message = "Error en la tara verificar vaso vacio"


class Scales(HX711):

    def __init__(self, d_out, pd_sck, channel: int = HX711.CHANNEL_A_128):
        super(Scales, self).__init__(d_out, pd_sck, channel)
        self._offset = 0
        self._factor = 1
        # self.power_off()

    def reset(self):
        self.power_off()
        self.power_on()

    def set_factor(self, factor):
        self._factor = factor
        return self._factor

    def tare(self, samples, delay):
        self._offset = 0
        self._offset = mean(self.get_samples(samples, delay, False))

    def raw_value(self):
        return self.read() - self._offset

    def get_samples(self, n, delay, error_control=True):
        # self.power_on()
        samples = []
        i = 0
        error = 0
        while i <= n and error*100/n < 20:
            sample = self.raw_value()
            if sample >= 0:
                samples.append(sample)
                acum = (sample - samples[i-1])/n + samples[i-1]
                samples[i] = acum
                i += 1
            else:
                if error_control:
                    print(error, error*100/n < 20)
                    error += 1

            sleep_us(delay)

        if error*100/n >= 20:
            raise TareError

        # self.power_off()
        return samples

    def get_offset(self, raw=False):
        if raw:
            return self._offset
        else:
            return self._offset/self._factor

    def get_factor(self):
        return self._factor

    def get_value(self, samples=10, delay=10, error_control=True):
        data = self.get_samples(samples, delay, error_control)
        xbar = mean(data)
        return [xbar, stdev(data, xbar)]

# 269611.7
# 1110832.0,