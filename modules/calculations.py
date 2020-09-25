from uarray import array

def _spline(t, t0, t1, t2, t3, p0, p1, p2, p3):
    """
    https://en.wikipedia.org/wiki/Centripetal_Catmull%E2%80%93Rom_spline
    """

    _a1_x = (t1-t)/(t1-t0)*p0[0] + (t-t0)/(t1-t0)*p1[0]
    _a2_x = (t2-t)/(t2-t1)*p1[0] + (t-t1)/(t2-t1)*p2[0]
    _a3_x = (t3-t)/(t3-t2)*p2[0] + (t-t2)/(t3-t2)*p3[0]

    _b1_x = (t2-t)/(t2-t0)*_a1_x + (t-t0)/(t2-t0)*_a2_x
    _b2_x = (t3-t)/(t3-t1)*_a2_x + (t-t1)/(t3-t1)*_a3_x

    _c_x = (t2-t)/(t2-t1)*_b1_x + (t-t1)/(t2-t1)*_b2_x

    _a1_y = (t1-t)/(t1-t0)*p0[1] + (t-t0)/(t1-t0)*p1[1]
    _a2_y = (t2-t)/(t2-t1)*p1[1] + (t-t1)/(t2-t1)*p2[1]
    _a3_y = (t3-t)/(t3-t2)*p2[1] + (t-t2)/(t3-t2)*p3[1]

    _b1_y = (t2-t)/(t2-t0)*_a1_y + (t-t0)/(t2-t0)*_a2_y
    _b2_y = (t3-t)/(t3-t1)*_a2_y + (t-t1)/(t3-t1)*_a3_y

    _c_y = (t2-t)/(t2-t1)*_b1_y + (t-t1)/(t2-t1)*_b2_y

    return _c_x, _c_y


def _do_spline(target, n_step, step,  p, k, t0, t1, t2, t3, xmax, xmin, ymin, ymax, section, i):
    xmin = xmin
    ymin = ymin
    xmax = xmax
    ymax = ymax

    for j in range(n_step):
        if section == 0:
            cx, cy = _spline(t1+j*step, t0, t1, t2, t3, (p[0], k[0]), (p[0], k[0]), (p[1], k[1]), (p[2], k[2]))
        if section == 1:
            cx, cy = _spline(t1+j*step, t0, t1, t2, t3, (p[i], k[i]), (p[i+1], k[i+1]), (p[i+2], k[i+2]), (p[i+3], k[i+3]))
        if section == -1:
            cx, cy = _spline(t1+j*step, t0, t1, t2, t3, (p[-3], k[-3]), (p[-2], k[-2]), (p[-1], k[-1]), (p[-1], k[-1]))

        # print(target, xmin, cx, xmax)
        if xmin < cx < target:
            xmin = cx
            ymin = cy

        if target < cx < xmax:
            xmax = cx
            ymax = cy

        if cx > target and cx > xmax:
            result = _punto_en_recta(target, # x
                                    xmin,  # x1
                                    ymin,  # y1
                                    xmax,  # x2
                                    ymax   # y2
                                    )
            return result

    # print(xmin, target, xmax)
    if section == -1:
        result = _punto_en_recta(target, # x
                                xmin,  # x1
                                ymin,  # y1
                                xmax,  # x2
                                ymax   # y2
                                )
        return result

    return None


def spline_curve_point(target, p, k, n_step=64, alpha=0.5):

    _xmin = 0
    _ymin = None
    _xmax = 1204
    _ymax = None

    if target == 0:
        return 0
    if target == 1024:
        return 0

    # first curve
    t0 = 0
    # for numerical stability (divide-by-zero)
    t1 = 0.1**alpha + t0
    t2 = ((p[1]-p[0])**2 + (k[1]-k[1])**2)**alpha + t1
    t3 = ((p[2]-p[1])**2 + (k[1]-k[1])**2)**alpha + t2
    _step = (t2-t1) / n_step

    _sp = _do_spline(target, n_step, _step,  p, k, t0, t1, t2, t3, _xmax, _xmin, _ymin, _ymax, 0, None)
    if _sp is not None:
        return _sp

    # middle curve
    for i in range(len(p)-3):
        t0 = 0
        t1 = ((p[i+1]-p[i])**2 + (k[i+1]-k[i])**2)**alpha + t0
        t2 = ((p[i+2]-p[i+1])**2 + (k[i+2]-k[i+1])**2)**alpha + t1
        t3 = ((p[i+3]-p[i+2])**2 + (k[i+3]-k[i+2])**2)**alpha + t2
        _step = (t2-t1) / n_step

        _sp = _do_spline(target, n_step, _step,  p, k, t0, t1, t2, t3, _xmax, _xmin, _ymin, _ymax, 1, i)
        if _sp is not None:
            return _sp

    # last curve
    t0 = 0
    t1 = ((p[-2]-p[-3])**2 + (k[-2]-k[-3])**2)**alpha + t0
    t2 = ((p[-1]-p[-2])**2 + (k[-1]-k[-2])**2)**alpha + t1
    t3 = 0.1**alpha + t2 # for numerical stability (divide-by-zero)
    _step = (t2-t1) / n_step

    _sp = _do_spline(target, n_step, _step,  p, k, t0, t1, t2, t3, _xmax, _xmin, _ymin, _ymax, -1, None)
    if _sp is not None:
        return _sp


def _punto_en_recta(x, x1, y1, x2, y2):
    # (x-x1)/(x2-x1) = (y-y1)/(y2-y1)
    # y = mx+n
    print(x, x1, y1, x2, y2)
    _m = (y2-y1) / (x2-x1)
    # print (m)
    _y = _m*(x-x1) + y1
    return _y


def correct_temperature(relacion, temp_b, offset):

    #TODO agrega uso de RF G8
    tabla_correla = array('i', [12, 13, 14, 14, 12, 9, 5, 2, 53, 52, 49, 43, 35, 25, 13, 8]) #Empiricos copiados del excel
    tabla_corregida = [v+v*0.006*(360-offset) if i < 8 else v+v*0.005*(360-offset) for i, v in enumerate(tabla_correla)] #correccion de offsetde la tabla
    indice = 7+int(relacion/128) if temp_b < 22 else 0 + int(relacion/128)

    return relacion+tabla_corregida[indice+1]*(temp_b-22)/64
