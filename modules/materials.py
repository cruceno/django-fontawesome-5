import ujson
import uos, uio
from uarray import array

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


def make_material_index():
    materials = get_iterator()
    with uio.open('data/mat_index.dat', 'w') as ifile:
        for material in materials:
            with open('/'.join([MATERIAL_PATH, material[0]]), 'r') as f:
                data = ujson.load(f)
                ifile.write("{}\t{}\n".format(data["code"], data["name"]))
    return True


def get_mat_index():
    with uio.open('data/mat_index.dat', 'r') as f:
        index = f.read()
    return index


def material_from_code(code):
    obj = Material()
    try:
        with open('/'.join([MATERIAL_PATH, "{}.json".format(code)]), 'r') as f:
            data = ujson.load(f)
            obj.code = data["code"]
            obj.name = data["name"]
            obj.hum_rf = array('i', data["hum_rf"])
            obj.c_coef = data["c_coef"]
            obj.t_coef = data["t_coef"]
            obj.slope = data["slope"]
            obj.y0 = data["y0"]
            f.close()
            return obj
    except:
        return None


def remove_material(code):
    try:
        uos.remove('/'.join([MATERIAL_PATH, "{}.json".format(code)]))
        return True
    except:
        return False


def add_material(material_dict):
    try:
        with uio.open('/'.join([MATERIAL_PATH, material_dict['code']+'.json']), 'w') as f:
            ujson.dump(material_dict, f)
            return True
    except:
        return True

