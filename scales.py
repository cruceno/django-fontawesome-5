from hx711 import HX711
from utime import sleep, sleep_us
from statistics import mean, stdev


class Scales(HX711):

    def __init__(self, d_out, pd_sck, channel: int = HX711.CHANNEL_A_128):
        super(Scales, self).__init__(d_out, pd_sck, channel)
        self.offset = 0
        self.factor = 1

    def reset(self):
        self.power_off()
        self.power_on()

    def tare(self):
        self.offset = self.measure()[0]

    def raw_value(self):
        return self.read() - self.offset

    def get_samples(self, n=30, delay=200, raw=True):
        samples = []
        for _ in range(n + 1):
            if raw:
                samples.append(self.raw_value())
            else:
                samples.append(self.raw_value()/self.factor)
            sleep_us(delay)
        return samples

    def get_offset(self, raw=False):
        if raw:
            return self.offset
        else:
            return self.offset/self.factor

    def averaged(self, samples=10):
        data = self.get_samples(samples)
        xbar = mean(data)
        return [xbar, stdev(data, xbar)]

    def averaged_w(self, samples=10):
        data = self.get_samples(samples, raw=False)
        xbar = mean(data)
        return [xbar, stdev(data, xbar)]

    def measure(self, st=3, samples=30, raw=True):
        for t in range(st+1):
            print('Estabilizando: {}'.format(t))
            sleep(t)
        print('Midiendo...')
        if raw:
            return self.averaged(samples)
        else:
            return self.averaged_w(samples)
