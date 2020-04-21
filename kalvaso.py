def spline(t, t0, t1, t2, t3, p0, p1, p2, p3):

    a1_x = (t1-t)/(t1-t0)*p0[0] + (t-t0)/(t1-t0)*p1[0]
    a2_x = (t2-t)/(t2-t1)*p1[0] + (t-t1)/(t2-t1)*p2[0]
    a3_x = (t3-t)/(t3-t2)*p2[0] + (t-t2)/(t3-t2)*p3[0]

    b1_x = (t2-t)/(t2-t0)*a1_x + (t-t0)/(t2-t0)*a2_x
    b2_x = (t3-t)/(t3-t1)*a2_x + (t-t1)/(t3-t1)*a3_x

    c_x  = (t2-t)/(t2-t1)*b1_x + (t-t1)/(t2-t1)*b2_x

    a1_y = (t1-t)/(t1-t0)*p0[1] + (t-t0)/(t1-t0)*p1[1]
    a2_y = (t2-t)/(t2-t1)*p1[1] + (t-t1)/(t2-t1)*p2[1]
    a3_y = (t3-t)/(t3-t2)*p2[1] + (t-t2)/(t3-t2)*p3[1]

    b1_y = (t2-t)/(t2-t0)*a1_y + (t-t0)/(t2-t0)*a2_y
    b2_y = (t3-t)/(t3-t1)*a2_y + (t-t1)/(t3-t1)*a3_y

    c_y  = (t2-t)/(t2-t1)*b1_y + (t-t1)/(t2-t1)*b2_y

    return c_x, c_y


def spline_curve(p, n_step=1024, alpha=0.5 ):

    curve = list()

    # first curve
    t0 = 0
    t1 = (0.1)**alpha + t0 # for numerical stability (divide-by-zero)
    t2 = ((p[1][0]-p[0][0])**2 + (p[1][1]-p[0][1])**2)**alpha + t1
    t3 = ((p[2][0]-p[1][0])**2 + (p[2][1]-p[1][1])**2)**alpha + t2
    step = (t2-t1) / n_step
    # print ("First: {}, {}, {}, {}, {}".format(t0, t1,t2,t3,step))

    for j in range(n_step):
        cx, cy = spline(t1+j*step, t0, t1, t2, t3, p[0], p[0], p[1], p[2])
        curve.append([cx, cy])

    # middle curve
    for i in range(len(p)-3):
        t0 = 0
        t1 = ((p[i+1][0]-p[i][0])**2 + (p[i+1][1]-p[i][1])**2)**alpha + t0
        t2 = ((p[i+2][0]-p[i+1][0])**2 + (p[i+2][1]-p[i+1][1])**2)**alpha + t1
        t3 = ((p[i+3][0]-p[i+2][0])**2 + (p[i+3][1]-p[i+2][1])**2)**alpha + t2
        step = (t2-t1) / n_step
        # print ("Middle: {}, {}, {}, {}, {}".format(t0, t1,t2,t3,step))

        for j in range(n_step):
            cx, cy = spline(t1+j*step, t0, t1, t2, t3, p[i], p[i+1], p[i+2], p[i+3])
            curve.append([cx, cy])

    # last curve
    t0 = 0
    t1 = ((p[-2][0]-p[-3][0])**2 + (p[-2][1]-p[-3][1])**2)**alpha + t0
    t2 = ((p[-1][0]-p[-2][0])**2 + (p[-1][1]-p[-2][1])**2)**alpha + t1
    t3 = (0.1)**alpha + t2 # for numerical stability (divide-by-zero)
    step = (t2-t1) / n_step

    # print ("Last: {}, {}, {}, {}, {}".format(t0, t1,t2,t3,step))
    for j in range(n_step):
        cx, cy = spline(t1+j*step, t0, t1, t2, t3, p[-3], p[-2], p[-1], p[-1])
        curve.append([cx, cy])

    return curve

def punto_en_recta(x, x1, y1, x2, y2):
    # (x-x1)/(x2-x1) = (y-y1)/(y2-y1)
    # y = mx+n
    print(x, x1, y1, x2, y2)

    m = (y2-y1) / (x2-x1)
    # print (m)
    y = m*(x-x1) +y1
    return x, y
#
# def get_calibrated_value(pts):
#
#     kalvaso = []
#     patron = range(0, 1025, 64)
#
#     for i, x in enumerate(patron):
#         kalvaso.append([x, pts[i]])
#
#     equipo = []
#     cv = spline_curve(kalvaso, 1024, alpha=0.5)
#     x, y = zip(*cv)
#
#     for target in patron:
#         rect_p = [(x, y[i]) for i, x in enumerate(x) if target-0.5 <= x <=target + 0.5]
#
#         result = punto_en_recta(target,   # x
#                                 rect_p[0][0],  # x1
#                                 rect_p[0][1],  # y1
#                                 rect_p[-1][0], # x2
#                                 rect_p[-1][1]  # y2
#                                 )
#
#
#         equipo.append([result[0], int(target+result[1]*-1)])
#
#     px, py = zip(*patron)
#     ex, ey = zip(*equipo)
#
#     return py, ey
#
