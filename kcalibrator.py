#!python3
# coding: utf-8
# author: Victor Shapovalov (@ArtificalSUN), 2020
# version: 0.1.1


# this script generates pattern fot Linear Advance K-factor calibration for Marlin (and other firmwares which use M900 to adjust pressure control algorithms)
# the pattern consists of a rectangular wall printed with sharp changes in speed and with K-factor increasing from bottom to top
# print the pattern and find the height where it looks the best
# corners should not bulge, flow should be homogeneous with as little influence from speed changes as possible, seam should be barely noticeable
# calculate desired K-factor from this height and parameters u used to generate the pattern
# good luck

import os, sys
from math import pi, sqrt

speed_slow = 20 # slow speed for calibration pattern
speed_fast = 90 # fast speed for calibrtion pattern
k_start = 0.2 # \
k_end = 0.6   # | start, stop and step values for K-factor calibration
k_step = 0.02 # /
layers_per_k = 5 # number of layers printed with any specific K-factor
z_offset=0.16 # Z-offset
size = (120, 60) # (X, Y) size of the pattern
retract = (4, 30) # (length, speed) for retractions
bed_size = (235,180) # (X, Y) size of the bed
temperature = (250,80) # (hotend, bed) temperatures
path_spd_fractions = (0.2, 0.6, 0.2) #fractions for pattern parts printed with slow and fast speeds
use_G29 = True # adds G29 to start g-code (for autoleveling)
retract_at_layer_change = True # retract at layer change
double_perimeter = True # print test with two perimeters instead of one

def_fil_dia = 1.75 # filament diameter in mm
def_line_width = 0.5 # line width
def_layer = 0.2 # layer height
def_speed_print = 60 # default printing speed (first layer, etc.)
def_speed_travel = 160 # defauld traver speed
def_cooling = 127 # part cooling fan speed (0-255)

def frange(start, stop, step): #float range!
    while start < stop:
        yield start
        start += step

def moveabs(position, *args):
    new_position = position[:]
    try:
        for i, coordinate in enumerate(args): new_position[i]=coordinate
    except IndexError: pass
    return new_position

def moverel(position, *args):
    new_position = position[:]
    try:
        for i, coordinate in enumerate(args): new_position[i]+=coordinate
    except IndexError: pass
    return new_position

class Extruder:
    def __init__(self, e):
        self.e = e
    def extrude(self, l, w=def_line_width, h=def_layer, flow=1.0, dia = def_fil_dia):
        V = flow*w*l*h
        L = V*4/(pi*dia**2)
        self.e+=L
        return self.e

def rectangle(x_center, y_center, x_size, y_size):
    return [(x_center-x_size/2, y_center-y_size/2), (x_center-x_size/2, y_center+y_size/2), (x_center+x_size/2, y_center+y_size/2), (x_center+x_size/2, y_center-y_size/2)]

def G1(position, length, speed):
    return "G1 X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f} E{l:.5f} F{s}\n".format(p=position, l=length, s=speed*60)

def G0(position, speed):
    return "G0 X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f} F{s}\n".format(p=position, s=speed*60)

def M900(k):
    return "M900 K{kf}\nM117 K={kf:.3F}\n".format(kf=k)

def dist(start, end):
    return sqrt((end[0]-start[0])**2+(end[1]-start[1])**2+(end[2]-start[2])**2)

ex = Extruder(0)

gcode_start = \
"""M190 S{T_b}
M109 S{T_h}
M106 S{C}
G28{G29}
G90
;M83
M900 K0
G92 E0
G0 Z{zo:.3f} F300
G92 Z{zl:.3f}
G0 Z2.0 F600
G0 X{X1:.3f} Y{Y1:.3f} Z0.2 F{F_t} ;Move to start position
G1 X{X1:.3f} Y{Y2:.3f} F{F_p} E{E1:.5f} ;Draw the first line
G0 X{X2:.3f} Y{Y2:.3f} F{F_t} ;Move to side a little
G1 X{X2:.3f} Y{Y1:.3f} F{F_p} E{E2:.5f} ;Draw the second line
G92 E0 ;Reset Extruder
G0 Z2 F600""".format(T_h=temperature[0], T_b=temperature[1], C=def_cooling, zl=def_layer, zo=def_layer+z_offset, F_t=def_speed_travel*60, F_p=def_speed_print*60, X1=1, Y1=10,
                        Y2=bed_size[1]-10, X2=1+def_line_width, E1=ex.extrude(bed_size[1]-20), E2 = ex.extrude(bed_size[1]-20), G29 = "\nG29" if use_G29 else "")

gcode_end = \
"""M104 S0
M140 S0
M107
G91
G1 E-{R} F{RS}
G0 Z5 F600
G90
G0 X0 Y0 F{F_t}""".format(R=retract[0], RS = retract[1]*60, F_t = def_speed_travel*60)

gcode = [gcode_start,]

#first layer
ex.e=0
bed_center = (bed_size[0]/2, bed_size[1]/2)
current_pos = [1+def_line_width, 10, def_layer]
# current_e = 0
layer = []
for i in range(-5, 5):
    loop = rectangle(bed_size[0]/2, bed_size[1]/2, size[0]+2*i*def_line_width, size[1]+2*i*def_line_width)
    next_pos = moveabs(current_pos, loop[3][0], loop[3][1])
    layer.append(G0(next_pos, def_speed_travel))
    current_pos = next_pos[:]
    for point in loop:
        next_pos = moveabs(current_pos, point[0], point[1])
        # next_e = ex.extrude(dist(current_pos, next_pos))
        layer.append(G1(next_pos, ex.extrude(dist(current_pos, next_pos)), def_speed_print))
        current_pos = next_pos[:]
        # current_e += next_e
gcode.extend(layer)
gcode.extend(["G92 E0\n",
              "G1 E-{R} F{S}\n".format(R=retract[0], S=retract[1]*60) if retract_at_layer_change else ""])

#pattern generation
current_z = current_pos[2]
corners = rectangle(bed_size[0]/2,bed_size[1]/2, size[0], size[1])
if double_perimeter:
    size2 = (size[0]+2*def_line_width, size[1]+2*def_line_width)
    corners2 = rectangle(bed_size[0]/2,bed_size[1]/2, size2[0], size2[1])
for k in frange(k_start, k_end+k_step, k_step):
    gcode.append(M900(k))
    for i in range(layers_per_k):
        current_z+=def_layer
        layer = []
        ex.e = 0
        layer.extend([G0((bed_center[0], bed_center[1]+size[1]/2, current_z), def_speed_travel),
                      "G1 E0 F{S}\n".format(S=retract[1]*60) if retract_at_layer_change else "",
                      G1((corners[1][0]+size[0]*path_spd_fractions[0], corners[1][1], current_z), ex.extrude(abs(corners[1][0]+size[0]*path_spd_fractions[0]-bed_center[0])), speed_slow),
                      G1((corners[1][0], corners[1][1], current_z), ex.extrude(abs(size[0]*path_spd_fractions[2])), speed_fast),
                      G1((corners[1][0], corners[0][1]+size[1]/2, current_z), ex.extrude(abs(size[1]/2)), speed_fast),
                      G1((corners[0][0], corners[0][1], current_z), ex.extrude(abs(size[1]/2)), speed_slow),
                      G1((corners[0][0]+size[0]*path_spd_fractions[0], corners[0][1], current_z), ex.extrude(abs(size[0]*path_spd_fractions[0])), speed_slow),
                      G1((corners[3][0]-size[0]*(path_spd_fractions[2]), corners[0][1], current_z), ex.extrude(abs(size[0]*path_spd_fractions[1])), speed_fast),
                      G1((corners[3][0], corners[3][1], current_z), ex.extrude(abs(size[0]*path_spd_fractions[2])), speed_slow),
                      G1((corners[3][0], corners[3][1]+size[1]/2, current_z), ex.extrude(abs(size[1]/2)), speed_slow),
                      G1((corners[2][0], corners[2][1], current_z), ex.extrude(abs(size[1]/2)), speed_fast),
                      G1((corners[2][0]-size[0]*path_spd_fractions[2], corners[2][1], current_z), ex.extrude(abs(size[0]*path_spd_fractions[2])), speed_fast),
                      G1((bed_center[0]+def_line_width/2, bed_center[1]+size[1]/2, current_z), ex.extrude(abs(bed_center[0]+def_line_width/2-corners[2][0])), speed_slow),
                      "G92 E0\n",
                      "G1 E-{R} F{S}\n".format(R=retract[0], S=retract[1]*60) if (retract_at_layer_change and not double_perimeter) else ""])
        current_pos = (bed_center[0]+def_line_width/2, bed_center[1]+size[1]/2, current_z)

        if double_perimeter:
            ex.e = 0
            layer.extend([G0((bed_center[0], bed_center[1]+size2[1]/2, current_z), def_speed_travel),
                          "G1 E0 F{S}\n".format(S=retract[1]*60) if (retract_at_layer_change and not double_perimeter) else "",
                          G1((corners2[1][0]+size2[0]*path_spd_fractions[0], corners2[1][1], current_z), ex.extrude(abs(corners2[1][0]+size2[0]*path_spd_fractions[0]-bed_center[0])), speed_slow),
                          G1((corners2[1][0], corners2[1][1], current_z), ex.extrude(abs(size2[0]*path_spd_fractions[2])), speed_fast),
                          G1((corners2[1][0], corners2[0][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), speed_fast),
                          G1((corners2[0][0], corners2[0][1], current_z), ex.extrude(abs(size2[1]/2)), speed_slow),
                          G1((corners2[0][0]+size2[0]*path_spd_fractions[0], corners2[0][1], current_z), ex.extrude(abs(size2[0]*path_spd_fractions[0])), speed_slow),
                          G1((corners2[3][0]-size2[0]*(path_spd_fractions[2]), corners2[0][1], current_z), ex.extrude(abs(size2[0]*path_spd_fractions[1])), speed_fast),
                          G1((corners2[3][0], corners2[3][1], current_z), ex.extrude(abs(size2[0]*path_spd_fractions[2])), speed_slow),
                          G1((corners2[3][0], corners2[3][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), speed_slow),
                          G1((corners2[2][0], corners2[2][1], current_z), ex.extrude(abs(size2[1]/2)), speed_fast),
                          G1((corners2[2][0]-size2[0]*path_spd_fractions[2], corners2[2][1], current_z), ex.extrude(abs(size2[0]*path_spd_fractions[2])), speed_fast),
                          G1((bed_center[0]+def_line_width/2, bed_center[1]+size2[1]/2, current_z), ex.extrude(abs(bed_center[0]+def_line_width/2-corners2[2][0])), speed_slow),
                          "G92 E0\n",
                          "G1 E-{R} F{S}\n".format(R=retract[0], S=retract[1]*60) if retract_at_layer_change else ""])
            current_pos = (bed_center[0]+def_line_width/2, bed_center[1]+size2[1]/2, current_z)
        gcode.extend(layer)

gcode.append(gcode_end)
with open("KF_{b}_{e}_{s}.gcode".format(b=k_start, e=k_end, s=k_step), "w") as out:
    out.writelines(gcode)