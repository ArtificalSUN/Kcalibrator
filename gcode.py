from math import pi, sqrt, sin, cos


def frange(start, stop, step):
    """float range!"""
    while start < stop:
        yield start
        start += step


def moveabs(position, *args):
    """Absolute move from position to new_position"""
    new_position = position[:]
    try:
        for i, coordinate in enumerate(args): new_position[i] = coordinate
    except IndexError: pass
    return new_position


def moverel(position, *args):
    """Relative move from position to new_position"""
    new_position = position[:]
    try:
        for i, coordinate in enumerate(args): new_position[i] += coordinate
    except IndexError: pass
    return new_position


def cornerMoves(start_angle, radius, center):
    moves = []

    movements_per_quater_circle = 50
    for k in range(0, movements_per_quater_circle):
        angle = start_angle - (k / movements_per_quater_circle) * pi / 2
        moves.append((center[0] + cos(angle) * radius, center[1] + sin(angle) * radius))
    return moves


class Extruder:
    """virtual extruder class"""

    def __init__(self, e, config):
        self.e = e
        self.def_line_width = config.def_line_width
        self.def_layer = config.def_layer
        self.def_flow = 1.0
        self.def_fil_dia = config.def_fil_dia

    def extrude(self, l, width=None, height=None, flow=None, dia = None):
        f = float(flow) if flow else self.def_flow
        w = float(width) if width else self.def_line_width
        h = float(height) if height else self.def_layer
        d = float(dia) if dia else self.def_fil_dia
        V = f*w*l*h
        L = V*4/(pi*d**2)
        self.e+=L
        return self.e

    def retract(self): pass
    def deretract(self): pass


def rectangle(x_center, y_center, x_size, y_size):
    """construct rectangle from center"""
    return [(x_center-x_size/2, y_center-y_size/2),
            (x_center-x_size/2, y_center+y_size/2),
            (x_center+x_size/2, y_center+y_size/2),
            (x_center+x_size/2, y_center-y_size/2)]


def G1(position, length, speed):
    return "G1 X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f} E{l:.5f} F{s}\n".format(
        p=position, l=length, s=speed*60)


def G0(position, speed):
    return "G0 X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f} F{s}\n".format(
        p=position, s=speed*60)


def M900(k, fw = 'Marlin/Lerdge'):
    if fw == 'Marlin/Lerdge': return "M900 K{kf:.3f}\nM117 K={kf:.3f}\n".format(kf=k)
    elif fw == 'Klipper': return "SET_PRESSURE_ADVANCE ADVANCE={kf:.3f}\n".format(kf=k)
    elif fw == 'RepRapFirmware': return "M572 D0 S{kf:.3f}\n".format(kf=k)
    else: return "M900 K{kf:.3f}\nM117 K={kf:.3f}\n".format(kf=k)


def ABL(use, cmd ="G29"):
    if not use: return ""
    else: return cmd + "\n"


def dist(start, end):
    return sqrt((end[0]-start[0])**2+(end[1]-start[1])**2+(end[2]-start[2])**2)


def creategcode(config, version):
    print('[generator] Started creategcode')
    print('[generator] {}'.format(config))
    ex = Extruder(0, config)

    gcode_start = \
    """;Generated with {vs}
M190 S{T_b}
M109 S{T_h}
G28
{ABL}G90
M82
{zeroadv}G92 E0
G0 Z{zo:.3f} F300
G92 Z{zl:.3f}
G0 Z2 F600
M106 S{C}\n""".format(vs = version, T_h=config.temperature[0],
                      T_b=config.temperature[1],
                      C=int(config.def_cooling / 100 * 255),
                      zl=config.def_layer,
                      zo=config.def_layer + config.z_offset,
                      F_t=config.def_speed_travel * 60,
                      F_p=config.def_speed_print * 60, X1=1, Y1=10,
                      Y2=config.bed_size[1] - 10,
                      X2=1 + config.def_line_width,
                      E1=ex.extrude(config.bed_size[1] - 20),
                      E2 = ex.extrude(config.bed_size[1] - 20),
                      ABL = ABL(config.use_ABL, config.ABL_type),
                      zeroadv = M900(0, config.firmware))

    gcode_end = \
    """M104 S0
M140 S0
M107
G91{retr}
G0 Z5 F600
G90
G0 X0 Y0 F{F_t}""".format(
        retr = "" if config.retract_at_layer_change else "\nG1 E-{R} F{RS}".format(
            R=config.retract[0],
            RS=config.retract[1] * 60),
        F_t=config.def_speed_travel * 60)

    gcode = [gcode_start,]

    #first layer
    ex.e=0
    bed_center = (config.bed_size[0] / 2, config.bed_size[1] / 2) if not config.kinematics == "Delta" else (0.0, 0.0)
    current_pos = [1 + config.def_line_width, 10, config.def_layer]
    # current_e = 0
    layer = []

    brimStart = -10
    brim_line_width = config.def_line_width * 0.9
    for i in range(10, brimStart, -1):
        rect = rectangle(bed_center[0], bed_center[1], config.size[0] + 2 * i * brim_line_width, config.size[1] + 2 * i * brim_line_width)
        if i > 0:
            loop = []
            rect = rectangle(bed_center[0], bed_center[1], config.size[0] + 2 * i * brim_line_width, config.size[1] + 2 * i * brim_line_width)

            corner_radius = i*brim_line_width
            loop.append((rect[-1][0] - corner_radius, rect[-1][1]))

            center = (rect[0][0] + corner_radius, rect[0][1] + corner_radius)
            loop += cornerMoves(-pi / 2, corner_radius, center)

            center = (rect[1][0] + corner_radius, rect[1][1] - corner_radius)
            loop += cornerMoves(pi, corner_radius, center)

            center = (rect[2][0] - corner_radius, rect[2][1] - corner_radius)
            loop += cornerMoves(pi / 2, corner_radius, center)

            center = (rect[3][0] - corner_radius, rect[3][1] + corner_radius)
            loop += cornerMoves(0, corner_radius, center)
        else:
            loop = rect

        next_pos = moveabs(current_pos, loop[-1][0], loop[-1][1])
        layer.append(G0(next_pos, config.def_speed_travel))
        current_pos = next_pos[:]
        for point in loop:
            next_pos = moveabs(current_pos, point[0], point[1])
            # next_e = ex.extrude(dist(current_pos, next_pos))
            layer.append(G1(next_pos, ex.extrude(dist(current_pos, next_pos)), config.def_speed_print))
            current_pos = next_pos[:]
            # current_e += next_e
    gcode.extend(layer)
    gcode.extend(["G92 E0\n",
                "G1 E-{R} F{S}\n".format(R=config.retract[0], S=config.retract[1] * 60) if config.retract_at_layer_change else ""])

    #pattern generation
    current_z = current_pos[2]
    corners = rectangle(bed_center[0], bed_center[1], config.size[0], config.size[1])
    if config.double_perimeter:
        size2 = (config.size[0] + 2 * config.def_line_width, config.size[1] + 2 * config.def_line_width)
        corners2 = rectangle(bed_center[0],bed_center[1], size2[0], size2[1])
    for k in frange(config.k_start, config.k_end + config.k_step, config.k_step if config.k_start < config.k_end + config.k_step else -config.k_step):
        gcode.append(M900(k, config.firmware))
        for i in range(config.layers_per_k):
            current_z+=config.def_layer
            layer = []
            ex.e = 0
            layer.extend([G0((bed_center[0], bed_center[1] + config.size[1] / 2, current_z), config.def_speed_travel),
                        "G1 E0 F{S}\n".format(S=config.retract[1] * 60) if config.retract_at_layer_change else "",
                          G1((corners[1][0] + config.size[0] * config.path_spd_fractions[0], corners[1][1], current_z), ex.extrude(abs(corners[1][0] + config.size[0] * config.path_spd_fractions[0] - bed_center[0])), config.speed_slow),
                          G1((corners[1][0], corners[1][1], current_z), ex.extrude(abs(config.size[0] * config.path_spd_fractions[2])), config.speed_fast),
                          G1((corners[1][0], corners[0][1] + config.size[1] / 2, current_z), ex.extrude(abs(config.size[1] / 2)), config.speed_fast),
                          G1((corners[0][0], corners[0][1], current_z), ex.extrude(abs(config.size[1] / 2)), config.speed_slow),
                          G1((corners[0][0] + config.size[0] * config.path_spd_fractions[0], corners[0][1], current_z), ex.extrude(abs(config.size[0] * config.path_spd_fractions[0])), config.speed_slow),
                          G1((corners[3][0] - config.size[0] * (config.path_spd_fractions[2]), corners[0][1], current_z), ex.extrude(abs(config.size[0] * config.path_spd_fractions[1])), config.speed_fast),
                          G1((corners[3][0], corners[3][1], current_z), ex.extrude(abs(config.size[0] * config.path_spd_fractions[2])), config.speed_slow),
                          G1((corners[3][0], corners[3][1] + config.size[1] / 2, current_z), ex.extrude(abs(config.size[1] / 2)), config.speed_slow),
                          G1((corners[2][0], corners[2][1], current_z), ex.extrude(abs(config.size[1] / 2)), config.speed_fast),
                          G1((corners[2][0] - config.size[0] * config.path_spd_fractions[2], corners[2][1], current_z), ex.extrude(abs(config.size[0] * config.path_spd_fractions[2])), config.speed_fast),
                          G1((bed_center[0] + config.def_line_width / 2, bed_center[1] + config.size[1] / 2, current_z), ex.extrude(abs(corners[1][0] + config.size[0] * config.path_spd_fractions[0] - bed_center[0])), config.speed_slow),
                        "G92 E0\n",
                        "G1 E-{R} F{S}\n".format(R=config.retract[0], S=config.retract[1] * 60) if (config.retract_at_layer_change and not config.double_perimeter) else ""])
            current_pos = (bed_center[0] + config.def_line_width / 2, bed_center[1] + config.size[1] / 2, current_z)

            if config.double_perimeter:
                ex.e = 0
                layer.extend([G0((bed_center[0], bed_center[1]+size2[1]/2, current_z), config.def_speed_travel),
                            "G1 E0 F{S}\n".format(S=config.retract[1] * 60) if (config.retract_at_layer_change and not config.double_perimeter) else "",
                              G1((corners2[1][0] + size2[0] * config.path_spd_fractions[0], corners2[1][1], current_z), ex.extrude(abs(corners2[1][0] + size2[0] * config.path_spd_fractions[0] - bed_center[0])), config.speed_slow),
                              G1((corners2[1][0], corners2[1][1], current_z), ex.extrude(abs(size2[0] * config.path_spd_fractions[2])), config.speed_fast),
                              G1((corners2[1][0], corners2[0][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), config.speed_fast),
                              G1((corners2[0][0], corners2[0][1], current_z), ex.extrude(abs(size2[1]/2)), config.speed_slow),
                              G1((corners2[0][0] + size2[0] * config.path_spd_fractions[0], corners2[0][1], current_z), ex.extrude(abs(size2[0] * config.path_spd_fractions[0])), config.speed_slow),
                              G1((corners2[3][0] - size2[0] * (config.path_spd_fractions[2]), corners2[0][1], current_z), ex.extrude(abs(size2[0] * config.path_spd_fractions[1])), config.speed_fast),
                              G1((corners2[3][0], corners2[3][1], current_z), ex.extrude(abs(size2[0] * config.path_spd_fractions[2])), config.speed_slow),
                              G1((corners2[3][0], corners2[3][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), config.speed_slow),
                              G1((corners2[2][0], corners2[2][1], current_z), ex.extrude(abs(size2[1]/2)), config.speed_fast),
                              G1((corners2[2][0] - size2[0] * config.path_spd_fractions[2], corners2[2][1], current_z), ex.extrude(abs(size2[0] * config.path_spd_fractions[2])), config.speed_fast),
                              G1((bed_center[0] + config.def_line_width / 2, bed_center[1] + size2[1] / 2, current_z), ex.extrude(abs(corners[1][0] + size2[0] * config.path_spd_fractions[0] - bed_center[0])), config.speed_slow),
                            "G92 E0\n",
                            "G1 E-{R} F{S}\n".format(R=config.retract[0], S=config.retract[1] * 60) if config.retract_at_layer_change else ""])
                current_pos = (bed_center[0] + config.def_line_width / 2, bed_center[1] + size2[1] / 2, current_z)
            gcode.extend(layer)

    gcode.append(gcode_end)
    print('[generator] Stopped creategcode')
    return gcode
