import ujson
import uos
MATERIAL_PATH = "data/materials"


class Material(object):
    code = str()
    name = str()
    hum_rf = list()
    y0 = int()
    slope = int()
    t_coef = int()
    c_coef = int()
    date = str()


def get_iterator():
    return uos.ilistdir(MATERIAL_PATH)

def material_from_code(code):
    obj = Material()
    materials = get_iterator()
    for material in materials:
        if code == material[0].split('.')[0]:
            with open('/'.join([MATERIAL_PATH, material[0]]), 'r') as f:
                data = ujson.load(f)
                obj.code = data["code"]
                obj.name = data["name"]
                obj.hum_rf = data["hum_rf"]
                obj.c_coef = data["c_coef"]
                obj.t_coef = data["t_coef"]
                obj.slope = data["slope"]
                obj.y0 = data["y0"]
                return obj
    return None


def next_material(code):

    obj = Material()
    materials = get_iterator()
    material = materials.__next__()
    while material:
        if code == material[0].split('.')[0]:
            try:
                material = materials.__next__()
                with open('/'.join([MATERIAL_PATH, material[0]]), 'r') as f:
                    data = ujson.load(f)
                    obj.code = data["code"]
                    obj.name = data["name"]
                    obj.hum_rf = data["hum_rf"]
                    obj.c_coef = data["c_coef"]
                    obj.t_coef = data["t_coef"]
                    obj.slope = data["slope"]
                    obj.y0 = data["y0"]
                    return obj
            except StopIteration:
                return None
        material = materials.__next__()
    return False


def remove_material(code):
    materials = get_iterator()
    for material in materials:
        if code == material[0].split('.')[0]:
            uos.remove('/'.join([MATERIAL_PATH, material[0]]))
            return True
    return False


def add_material(material_dict):
    try:
        uos.stat('/'.join([MATERIAL_PATH, material_dict['code']]))
        return False

    except OSError:
        with open('/'.join([MATERIAL_PATH, material_dict['code']+'.json']), 'w') as f:
            ujson.dump(material_dict, f)
            return True

def update_material(material_dict):
    materials = get_iterator()
    for material in materials:
        if material_dict['code'] == material[0].split('.')[0]:
            with open('/'.join([MATERIAL_PATH, material_dict['code']+'.json']), 'w') as f:
                ujson.dump(material_dict, f)
                return True
    return False
