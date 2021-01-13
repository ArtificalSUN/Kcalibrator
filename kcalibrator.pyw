#!python3
# coding: utf-8
# author: Victor Shapovalov (@ArtificalSUN, https://github.com/ArtificalSUN), 2021
# Configuration contributed by Foreytor (https://github.com/Foreytor)
# version: 1.0.2

"""
This script generates pattern fot Linear Advance K-factor calibration for Marlin (and other firmwares which use M900 to adjust pressure control algorithms)
The pattern consists of a rectangular wall printed with sharp changes in speed and with K-factor increasing from bottom to top
Print the pattern and find the height where it looks the best
Corners should not bulge, flow should be homogeneous with as little influence from speed changes as possible, seam should be barely noticeable
Calculate desired K-factor from this height and parameters you used to generate the pattern
Good luck!
"""

versionstring = "Kcalibrator v1.0.2 (Victor Shapovalov, 2021)"
import os, sys, re
from math import pi, sqrt


import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fldg

import kcalibrator_gui as gui
import kcalibrator_gui_support as gui_support
import kcalibrator_settings as settings

def frange(start, stop, step): # float range!
    while start < stop:
        yield start
        start += step

def moveabs(position, *args): # absolute move from position to new_position
    new_position = position[:]
    try:
        for i, coordinate in enumerate(args): new_position[i]=coordinate
    except IndexError: pass
    return new_position

def moverel(position, *args): # relative move from position to new_position
    new_position = position[:]
    try:
        for i, coordinate in enumerate(args): new_position[i]+=coordinate
    except IndexError: pass
    return new_position


class Extruder: # virtual extruder class
    def __init__(self, e, currentConfig):
        self.e = e
        self.def_line_width = currentConfig.def_line_width
        self.def_layer = currentConfig.def_layer
        # self.flow = currentConfig.def_flow
        self.def_flow = 1.0
        self.def_fil_dia = currentConfig.def_fil_dia

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


def rectangle(x_center, y_center, x_size, y_size): # construct rectangle from center
    return [(x_center-x_size/2, y_center-y_size/2), (x_center-x_size/2, y_center+y_size/2), (x_center+x_size/2, y_center+y_size/2), (x_center+x_size/2, y_center-y_size/2)]

def G1(position, length, speed):
    return "G1 X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f} E{l:.5f} F{s}\n".format(p=position, l=length, s=speed*60)

def G0(position, speed):
    return "G0 X{p[0]:.3f} Y{p[1]:.3f} Z{p[2]:.3f} F{s}\n".format(p=position, s=speed*60)

def M900(k, fw = 'Marlin'):
    if fw=='Marlin': return "M900 K{kf}\nM117 K={kf:.3f}\n".format(kf=k)
    elif fw=='Klipper': return "SET_PRESSURE_ADVANCE ADVANCE={kf}\n".format(kf=k)
    elif fw=='RepRafFirmware': return "M572 D0 S{kf}\n".format(kf=k)

def ABL(use, ABL_cmd = "G29"):
    if not use: return ""
    else: return "\n"+ABL_cmd

def dist(start, end):
    return sqrt((end[0]-start[0])**2+(end[1]-start[1])**2+(end[2]-start[2])**2)


def creategcode(currentConfig):

    print('started creategcode')

    ex = Extruder(0, currentConfig)

    gcode_start = \
    """;Generated with {vs}
M190 S{T_b}
M109 S{T_h}
G28{G29}
G90
M82
M900 K0
G92 E0
G0 Z{zo:.3f} F300
G92 Z{zl:.3f}
G0 Z2 F600
M106 S{C}\n""".format(vs = versionstring, T_h=currentConfig.temperature[0], T_b=currentConfig.temperature[1], C=int(currentConfig.def_cooling/100*255), zl=currentConfig.def_layer, zo=currentConfig.def_layer+currentConfig.z_offset, F_t=currentConfig.def_speed_travel*60, F_p=currentConfig.def_speed_print*60, X1=1, Y1=10,
                            Y2=currentConfig.bed_size[1]-10, X2=1+currentConfig.def_line_width, E1=ex.extrude(currentConfig.bed_size[1]-20), E2 = ex.extrude(currentConfig.bed_size[1]-20), G29 = ABL(currentConfig.use_ABL, currentConfig.ABL_type))

    gcode_end = \
    """M104 S0
M140 S0
M107
G91{retr}
G0 Z5 F600
G90
G0 X0 Y0 F{F_t}""".format(retr = "" if currentConfig.retract_at_layer_change else "\nG1 E-{R} F{RS}".format(R=currentConfig.retract[0], RS = currentConfig.retract[1]*60), F_t = currentConfig.def_speed_travel*60)

    gcode = [gcode_start,]

    #first layer
    ex.e=0
    bed_center = (currentConfig.bed_size[0]/2, currentConfig.bed_size[1]/2) if not currentConfig.kinematics=="Delta" else (0.0, 0.0)
    current_pos = [1+currentConfig.def_line_width, 10, currentConfig.def_layer]
    # current_e = 0
    layer = []
    for i in range(-10, 10):
        loop = rectangle(bed_center[0], bed_center[1], currentConfig.size[0]+2*i*currentConfig.def_line_width, currentConfig.size[1]+2*i*currentConfig.def_line_width)
        next_pos = moveabs(current_pos, loop[3][0], loop[3][1])
        layer.append(G0(next_pos, currentConfig.def_speed_travel))
        current_pos = next_pos[:]
        for point in loop:
            next_pos = moveabs(current_pos, point[0], point[1])
            # next_e = ex.extrude(dist(current_pos, next_pos))
            layer.append(G1(next_pos, ex.extrude(dist(current_pos, next_pos)), currentConfig.def_speed_print))
            current_pos = next_pos[:]
            # current_e += next_e
    gcode.extend(layer)
    gcode.extend(["G92 E0\n",
                "G1 E-{R} F{S}\n".format(R=currentConfig.retract[0], S=currentConfig.retract[1]*60) if currentConfig.retract_at_layer_change else ""])

    #pattern generation
    current_z = current_pos[2]
    corners = rectangle(bed_center[0], bed_center[1], currentConfig.size[0], currentConfig.size[1])
    if currentConfig.double_perimeter:
        size2 = (currentConfig.size[0]+2*currentConfig.def_line_width, currentConfig.size[1]+2*currentConfig.def_line_width)
        corners2 = rectangle(bed_center[0],bed_center[1], size2[0], size2[1])
    for k in frange(currentConfig.k_start, currentConfig.k_end+currentConfig.k_step, currentConfig.k_step if currentConfig.k_start < currentConfig.k_end+currentConfig.k_step else -currentConfig.k_step):
        gcode.append(M900(k, currentConfig.firmware))
        for i in range(currentConfig.layers_per_k):
            current_z+=currentConfig.def_layer
            layer = []
            ex.e = 0
            layer.extend([G0((bed_center[0], bed_center[1]+currentConfig.size[1]/2, current_z), currentConfig.def_speed_travel),
                        "G1 E0 F{S}\n".format(S=currentConfig.retract[1]*60) if currentConfig.retract_at_layer_change else "",
                        G1((corners[1][0]+currentConfig.size[0]*currentConfig.path_spd_fractions[0], corners[1][1], current_z), ex.extrude(abs(corners[1][0]+currentConfig.size[0]*currentConfig.path_spd_fractions[0]-bed_center[0])), currentConfig.speed_slow),
                        G1((corners[1][0], corners[1][1], current_z), ex.extrude(abs(currentConfig.size[0]*currentConfig.path_spd_fractions[2])), currentConfig.speed_fast),
                        G1((corners[1][0], corners[0][1]+currentConfig.size[1]/2, current_z), ex.extrude(abs(currentConfig.size[1]/2)), currentConfig.speed_fast),
                        G1((corners[0][0], corners[0][1], current_z), ex.extrude(abs(currentConfig.size[1]/2)), currentConfig.speed_slow),
                        G1((corners[0][0]+currentConfig.size[0]*currentConfig.path_spd_fractions[0], corners[0][1], current_z), ex.extrude(abs(currentConfig.size[0]*currentConfig.path_spd_fractions[0])), currentConfig.speed_slow),
                        G1((corners[3][0]-currentConfig.size[0]*(currentConfig.path_spd_fractions[2]), corners[0][1], current_z), ex.extrude(abs(currentConfig.size[0]*currentConfig.path_spd_fractions[1])), currentConfig.speed_fast),
                        G1((corners[3][0], corners[3][1], current_z), ex.extrude(abs(currentConfig.size[0]*currentConfig.path_spd_fractions[2])), currentConfig.speed_slow),
                        G1((corners[3][0], corners[3][1]+currentConfig.size[1]/2, current_z), ex.extrude(abs(currentConfig.size[1]/2)), currentConfig.speed_slow),
                        G1((corners[2][0], corners[2][1], current_z), ex.extrude(abs(currentConfig.size[1]/2)), currentConfig.speed_fast),
                        G1((corners[2][0]-currentConfig.size[0]*currentConfig.path_spd_fractions[2], corners[2][1], current_z), ex.extrude(abs(currentConfig.size[0]*currentConfig.path_spd_fractions[2])), currentConfig.speed_fast),
                        G1((bed_center[0]+currentConfig.def_line_width/2, bed_center[1]+currentConfig.size[1]/2, current_z), ex.extrude(abs(bed_center[0]+currentConfig.def_line_width/2-corners[2][0])), currentConfig.speed_slow),
                        "G92 E0\n",
                        "G1 E-{R} F{S}\n".format(R=currentConfig.retract[0], S=currentConfig.retract[1]*60) if (currentConfig.retract_at_layer_change and not currentConfig.double_perimeter) else ""])
            current_pos = (bed_center[0]+currentConfig.def_line_width/2, bed_center[1]+currentConfig.size[1]/2, current_z)

            if currentConfig.double_perimeter:
                ex.e = 0
                layer.extend([G0((bed_center[0], bed_center[1]+size2[1]/2, current_z), currentConfig.def_speed_travel),
                            "G1 E0 F{S}\n".format(S=currentConfig.retract[1]*60) if (currentConfig.retract_at_layer_change and not currentConfig.double_perimeter) else "",
                            G1((corners2[1][0]+size2[0]*currentConfig.path_spd_fractions[0], corners2[1][1], current_z), ex.extrude(abs(corners2[1][0]+size2[0]*currentConfig.path_spd_fractions[0]-bed_center[0])), currentConfig.speed_slow),
                            G1((corners2[1][0], corners2[1][1], current_z), ex.extrude(abs(size2[0]*currentConfig.path_spd_fractions[2])), currentConfig.speed_fast),
                            G1((corners2[1][0], corners2[0][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), currentConfig.speed_fast),
                            G1((corners2[0][0], corners2[0][1], current_z), ex.extrude(abs(size2[1]/2)), currentConfig.speed_slow),
                            G1((corners2[0][0]+size2[0]*currentConfig.path_spd_fractions[0], corners2[0][1], current_z), ex.extrude(abs(size2[0]*currentConfig.path_spd_fractions[0])), currentConfig.speed_slow),
                            G1((corners2[3][0]-size2[0]*(currentConfig.path_spd_fractions[2]), corners2[0][1], current_z), ex.extrude(abs(size2[0]*currentConfig.path_spd_fractions[1])), currentConfig.speed_fast),
                            G1((corners2[3][0], corners2[3][1], current_z), ex.extrude(abs(size2[0]*currentConfig.path_spd_fractions[2])), currentConfig.speed_slow),
                            G1((corners2[3][0], corners2[3][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), currentConfig.speed_slow),
                            G1((corners2[2][0], corners2[2][1], current_z), ex.extrude(abs(size2[1]/2)), currentConfig.speed_fast),
                            G1((corners2[2][0]-size2[0]*currentConfig.path_spd_fractions[2], corners2[2][1], current_z), ex.extrude(abs(size2[0]*currentConfig.path_spd_fractions[2])), currentConfig.speed_fast),
                            G1((bed_center[0]+currentConfig.def_line_width/2, bed_center[1]+size2[1]/2, current_z), ex.extrude(abs(bed_center[0]+currentConfig.def_line_width/2-corners2[2][0])), currentConfig.speed_slow),
                            "G92 E0\n",
                            "G1 E-{R} F{S}\n".format(R=currentConfig.retract[0], S=currentConfig.retract[1]*60) if currentConfig.retract_at_layer_change else ""])
                current_pos = (bed_center[0]+currentConfig.def_line_width/2, bed_center[1]+size2[1]/2, current_z)
            gcode.extend(layer)

    gcode.append(gcode_end)
    path = fldg.asksaveasfilename(title = "Save the G-code", filetypes = (("G-code files","*.gcode"),("All files","*.*")), defaultextension = ".gcode", initialfile = "KF_{b}-{e}-{s}_H{t[0]}-B{t[1]}.gcode".format(b=currentConfig.k_start, e=currentConfig.k_end, s=currentConfig.k_step, t=currentConfig.temperature))
    # path = fldg.asksaveasfile(title = "Save the G-code", filetypes = (("G-code files","*.gcode"),("All files","*.*")), defaultextension = ".gcode", initialfile = "KF_{b}-{e}-{s}_H{t[0]}-B{t[1]}.gcode".format(b=currentConfig.k_start, e=currentConfig.k_end, s=currentConfig.k_step, t=currentConfig.temperature))
    with open(path, "w") as out:
        out.writelines(gcode)
    print('stopped creategcode')


def save_config():
    global currentConfig, top
    currentConfig.updatesettings(top)
    currentConfig.save_config(configPath)

def update_and_create():
    global currentConfig, top
    currentConfig.updatesettings(top)
    creategcode(currentConfig)

configPath = "Kcalibrator.cfg"
currentConfig = settings.SettingClass()
if os.path.exists(configPath):
    try: currentConfig.read_config(configPath)
    except: currentConfig.save_config(configPath)
else:
    currentConfig.save_config(configPath)

root = tk.Tk()
gui_support.set_Tk_var()
top = gui.Toplevel(root)
gui_support.init(root, top)

top.attach()
top.updateUI(currentConfig)
top.revalidate_all()
top.btn_SaveConfig.configure(command = save_config)
top.btn_Generate.configure(command = update_and_create)

# root.after(10, top.updateUI)
root.mainloop()