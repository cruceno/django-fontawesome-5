def spline(t, t0, t1, t2, t3, p0, p1, p2, p3):
    """
    https://en.wikipedia.org/wiki/Centripetal_Catmull%E2%80%93Rom_spline
    """

    a1_x = (t1-t)/(t1-t0)*p0[0] + (t-t0)/(t1-t0)*p1[0]
    a2_x = (t2-t)/(t2-t1)*p1[0] + (t-t1)/(t2-t1)*p2[0]
    a3_x = (t3-t)/(t3-t2)*p2[0] + (t-t2)/(t3-t2)*p3[0]

    b1_x = (t2-t)/(t2-t0)*a1_x + (t-t0)/(t2-t0)*a2_x
    b2_x = (t3-t)/(t3-t1)*a2_x + (t-t1)/(t3-t1)*a3_x

    c_x = (t2-t)/(t2-t1)*b1_x + (t-t1)/(t2-t1)*b2_x

    a1_y = (t1-t)/(t1-t0)*p0[1] + (t-t0)/(t1-t0)*p1[1]
    a2_y = (t2-t)/(t2-t1)*p1[1] + (t-t1)/(t2-t1)*p2[1]
    a3_y = (t3-t)/(t3-t2)*p2[1] + (t-t2)/(t3-t2)*p3[1]

    b1_y = (t2-t)/(t2-t0)*a1_y + (t-t0)/(t2-t0)*a2_y
    b2_y = (t3-t)/(t3-t1)*a2_y + (t-t1)/(t3-t1)*a3_y

    c_y = (t2-t)/(t2-t1)*b1_y + (t-t1)/(t2-t1)*b2_y

    return c_x, c_y


def do_spline(target, n_step, step,  p, k, t0, t1, t2, t3, xmax, xmin, ymin, ymax, section, i):

    for j in range(n_step):
        if section == 0:
            cx, cy = spline(t1+j*step, t0, t1, t2, t3, (p[0], k[0]), (p[0], k[0]), (p[1], k[1]), (p[2], k[2]))
        if section == 1:
            cx, cy = spline(t1+j*step, t0, t1, t2, t3, (p[i], k[i]),(p[i+1], k[i+1]),(p[i+2], k[i+2]), (p[i+3], k[i+3]))
        if section == -1:
            cx, cy = spline(t1+j*step, t0, t1, t2, t3, (p[-3], k[-3]), (p[-2], k[-2]), (p[-1], k[-1]), (p[-1], k[-1]))

        # print(target, xmin, cx, xmax)
        if xmin < cx < target:
            xmin = cx
            ymin = cy

        if target < cx < xmax:
            xmax = cx
            ymax = cy

        if cx > target and cx > xmax:
            result = punto_en_recta(target,   # x
                                    xmin,  # x1
                                    ymin,  # y1
                                    xmax,  # x2
                                    ymax   # y2
                                    )
            return result

    # print(xmin, target, xmax)
    if section == -1:
        result = punto_en_recta(target,   # x
                                xmin,  # x1
                                ymin,  # y1
                                xmax,  # x2
                                ymax   # y2
                                )
        return result

    return None

def spline_curve_point(target, p, k, n_step=64, alpha=0.5):

    xmin = 0
    ymin = None
    xmax = 1204
    ymax = None

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
    step = (t2-t1) / n_step

    sp = do_spline(target, n_step, step,  p, k, t0, t1, t2, t3, xmax, xmin, ymin, ymax, 0, None)
    if sp is not None:
        return sp


    # middle curve
    for i in range(len(p)-3):
        t0 = 0
        t1 = ((p[i+1]-p[i])**2 + (k[i+1]-k[i])**2)**alpha + t0
        t2 = ((p[i+2]-p[i+1])**2 + (k[i+2]-k[i+1])**2)**alpha + t1
        t3 = ((p[i+3]-p[i+2])**2 + (k[i+3]-k[i+2])**2)**alpha + t2
        step = (t2-t1) / n_step

        sp = do_spline(target, n_step, step,  p, k, t0, t1, t2, t3, xmax, xmin, ymin, ymax, 1, i)
        if sp is not None:
            return sp

    # last curve
    t0 = 0
    t1 = ((p[-2]-p[-3])**2 + (k[-2]-k[-3])**2)**alpha + t0
    t2 = ((p[-1]-p[-2])**2 + (k[-1]-k[-2])**2)**alpha + t1
    t3 = 0.1**alpha + t2 # for numerical stability (divide-by-zero)
    step = (t2-t1) / n_step

    sp = do_spline(target, n_step, step,  p, k, t0, t1, t2, t3, xmax, xmin, ymin, ymax, -1, None)
    if sp is not None:
        return sp

def punto_en_recta(x, x1, y1, x2, y2):
    # (x-x1)/(x2-x1) = (y-y1)/(y2-y1)
    # y = mx+n
    # print(x, x1, y1, x2, y2)
    m = (y2-y1) / (x2-x1)
    # print (m)
    y = m*(x-x1) +y1
    return y


def correct_temperature(relacion, temp_b, offset):
    #TODO agrega uso de RF G8
    tabla_correla = [12, 13, 14, 14, 12, 9, 5, 2, 53, 52, 49, 43, 35, 25, 13, 8] #Empiricos copiados del excel
    tabla_corregida = [v+v*0.006*(360-offset) if i < 8 else v+v*0.005*(360-offset) for i, v in enumerate(tabla_correla)] #correccion de offsetde la tabla
    indice = 7+int(relacion/128) if temp_b < 22 else 0 + int(relacion/128)

    return relacion+tabla_corregida[indice+1]*(temp_b-22)/64


def medicion_grano(
        p_peso,
        p_relacion,
        temp_v,
        temp_b,
        offset,
        m_t_coef,
        m_slope,
        m_y0,
        m_c_coef,
        kalvaso,
        m_curve,
        auxi
    ):
    # print(p_peso, p_relacion, offset)
    value = correct_temperature(p_relacion, temp_b, offset)
    # print("Relacion corregida por temperatura: {0:.2f}".format(value))
    x = range(0, 1025, 64)
    # y = [0,	29,	60,	98,	147, 178, 164, 127, 115, 97, 57, 27, 7, -2,	-4,	-2,	0]
    # print(kalvaso)
    correcion = spline_curve_point(value, x, kalvaso, 64, 0.5)
    # print("Correccion por patron: {0:.2f}".format(correcion))
    relacorr = value + correcion
    # print("Relacion corregida por patron: {0:.2f}".format(relacorr))
    relacion = (1024-relacorr-m_y0*2)*4*(m_slope/auxi)/p_peso
    # print("Relacion corregida por peso hectrolitrico: {0:.2f}".format(relacion))
    x = range(32, 1024, 32)
    # y =[0, 0, 26, 16, 16,16,16,15,16,16,16,16,17,16,17,17,16,17,17,16,17,17,16,17,17,16,17,17,16,255,0,0]
    # print(m_curve)
    h_acum = []
    for h in m_curve:
        if len(h_acum) == 0:
            h_acum.append(h)
        else:
            h_acum.append(h + h_acum[len(h_acum)-1])

    # print(h_acum)
    humedad = spline_curve_point(relacion, x, h_acum, 200, 0.5)

    # print("Humedad desde tabla material: {0:.1f}".format(humedad))

    h_final = humedad-(m_t_coef-80)/64*(temp_v-22)
    # print("Humedad corregida por temperatura: {0:.2f}".format(h_final))
    # print("Humedad: {0:.1f}".format(h_final/10))
    # print("Peso Hectolitrico: {0:.2f}".format(p_peso*m_c_coef*auxi/640))
    return round(h_final/10, 1), p_peso*m_c_coef*auxi/640



