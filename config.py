import ujson


def load_config():
    try:
        with open("config.json", 'rt') as f:
            configuration = ujson.load(f)
            return configuration

    except Exception as e:
        print(str(e))


def save_config(config):
    old_config = load_config()
    try:
        with open("config.json", 'w') as f:
            new_config = old_config.update(config)
            ujson.dump(new_config, f)

    except Exception as e:
        print(str(e))


def load_defaults():
    try:
        with open("default.json", 'rt') as f:
            configuration = ujson.load(f)
            save_config(configuration)
            return configuration

    except Exception as e:
        print(str(e))


def update_config(old, new):
    config = {}
    for key, value in new.items():
        if key in old:
            if isinstance(value, dict):
                config[key] = {}
                for k, v in value.items():
                    if k in old[key]:
                        config[key][k] = v
                    else:
                        return {"result": 404, "msg": "Keyword {} not found".format(k)}
            else:
                config[key] = value
        else:
            return {"result": 404, "msg": "Keyword {} not found".format(key)}
    old.update(config)
    return {"result": 200, "msg": "Configuracion actualizada"}

