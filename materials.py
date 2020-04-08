import json

class Material(object):
    def __init__(self,
                 code,
                 name,
                 curve,
                 y0,
                 slope,
                 t_coef,
                 c_coef,
                 date):

        self.code = code
        self.name = name
        self.curve = curve
        self.y0 = y0
        self.slope = slope
        self.t_coef = t_coef
        self.c_coef = c_coef
        self.updated = date


def material_from_json(json):
    #TODO: Convertir objeto json s , material
    pass


def material_to_json(material):
    #TODO crear objeto json desde material
    pass