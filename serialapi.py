import ujson

class SerialAPI(object):

    sending = False
    led = None
    _COMMANDS = {}
    __RESPONSES = {
        200: {"result": 200, "msg": "OK"},
        400: {"result": 400, "msg": "No se reconoce la instruccion enviada"},
        500: {"result": 500, "msg": "Parte del hardware no está funcionando como debe y el equipo debe \
    ser revisado por personal técnico calificado"},
        304: {"result": 304, "msg": "No se han realizado cambios todo actualizado"}
    }

    def __init__(self, uart):
        # DOCME: Documentar seleccion de UART
        self.uart = uart
        self.sending = False

    def write_response(self, response):

        self.sending = True
        try:
            self.uart.write(response.encode('utf8'))
            self.sending = False
            # print("Ok")

        except Exception as e:
            self.sending = False
            # print("Error: {}".format(e))

    def read_command(self):
        if not self.sending:
            if not self.uart.any():
                pass
            else:
                cmd = self.uart.readline()
                self.exec_cmd(cmd)

    def exec_cmd(self, incoming):
        #Separa el comando de los parametros

        cmd = incoming.decode().strip('\n')
        # print(cmd)
        action = cmd.split(' ')[0]
        if len(cmd) >= 1:
            action = action.split('/')
            json_str = " ".join(cmd.split(' ')[1:])
            if len(action) == 2:
                # Instrucciones sin method
                params = None
                try:
                    try:
                        if json_str:
                            params = ujson.loads(json_str)
                    except Exception as e:
                        self.response_code(400, str(e))

                    response = self._COMMANDS[cmd.split(' ')[0]](params)
                    self.write_response(str(response)+"\n")
                except Exception as e:
                    self.response_code(500, "Error al ejecutar el comando: {}".format(str(e)))

            elif len(action) == 3:
                #Instrucciones que incluyen method
                method = action[1]
                params = None
                try:
                    if method == 'post':
                        try:
                            params = ujson.loads(json_str)
                        except Exception as e:
                            return self.response_code(400, str(e))

                    response = self._COMMANDS[cmd.split(' ')[0]](method, params)
                    self.write_response(ujson.dumps(response)+"\n")

                except Exception as e:
                    self.response_code(500, "Error al ejecutar el comando: {}".format(str(e)))
            else:
                return self.response_code(400)
        else:
            return self.response_code(400)

    def add_command(self, name, cmd):
        self._COMMANDS[name] = cmd

    def response_code(self, code, msg=None):
        response = self.__RESPONSES[code]
        if msg is not None:
            response['msg'] = str(msg)
        return self.write_response(ujson.dumps(response)+'\n')
