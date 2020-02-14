import _thread
import utime

class SerialAPI():

    sending = False
    led = None
    _COMMANDS = {}

    def __init__(self, uart):

        self.uart = uart
        self.sending = False
        # self.start_trhead()

    def write_response(self, response):

        self.sending = True
        self.uart.write(response.encode('utf8'))
        self.sending = False

    def read_command(self):
        if not self.sending:
            if not self.uart.any():
                pass
            else:
                cmd = self.uart.readline()
                self.exec_cmd(cmd)

    def exec_cmd(self, cmd):
        cmd = cmd.decode().strip('\n').split(' ')
        try:
            if len(cmd) > 1:
                response = self._COMMANDS[cmd[0]](*cmd[1:])
                # print(response)
                self.write_response(str(response))
                self.write_response('\n')
            else:
                # self.write_response('Ejecutando comando: {}'.format(cmd[0]))
                response = self._COMMANDS[cmd[0]]()
                # print(response)
                self.write_response(str(response))
                self.write_response('\n')

        except Exception as e:
            self.write_response(u"Comando no válido: {}\n".format(str(e)))

    def add_command(self, name, cmd):
        self._COMMANDS[name] = cmd
