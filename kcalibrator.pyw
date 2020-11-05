#!python3
# coding: utf-8
# author: Victor Shapovalov (@ArtificalSUN, https://github.com/ArtificalSUN), 2020
# GUI and configuration contributed by Foreytor (https://github.com/Foreytor)
# version: 0.2.1

"""
This script generates pattern fot Linear Advance K-factor calibration for Marlin (and other firmwares which use M900 to adjust pressure control algorithms)
The pattern consists of a rectangular wall printed with sharp changes in speed and with K-factor increasing from bottom to top
Print the pattern and find the height where it looks the best
Corners should not bulge, flow should be homogeneous with as little influence from speed changes as possible, seam should be barely noticeable
Calculate desired K-factor from this height and parameters you used to generate the pattern
Good luck!
"""

import os, sys, re, configparser
from math import pi, sqrt

try:
    import Tkinter as tk
except ImportError:
    import tkinter as tk

try:
    import ttk
    py3 = False
except ImportError:
    import tkinter.ttk as ttk
    py3 = True

class SettingClass():
    """
    Class to handle parameters for pattern generation and g-code output
    """
    def __init__(self):
        self.speed_slow = 20.0 # slow speed for calibration pattern
        self.speed_fast = 100.0 # fast speed for calibrtion pattern
        self.k_start = 0.0 # \
        self.k_end = 0.2   # | start, stop and step values for K-factor calibration
        self.k_step = 0.01 # /
        self.layers_per_k = 5 # number of layers printed with any specific K-factor
        self.z_offset=0.0 # Z-offset
        self.size = (140.0, 70.0) # (X, Y) size of the pattern
        self.retract = (4.0, 30.0) # (length, speed) for retractions
        self.bed_size = (200.0, 200.0) # (X, Y) size of the bed
        self.temperature = (210, 60) # (hotend, bed) temperatures
        self.path_spd_fractions = (0.2, 0.6, 0.2) #fractions for pattern parts printed with slow and fast speeds
        self.use_G29 = False # adds G29 to start g-code (for autoleveling)
        self.retract_at_layer_change = True # retract at layer change
        self.double_perimeter = False # print test with two perimeters instead of one

        self.def_fil_dia = 1.75 # filament diameter in mm
        self.def_line_width = 0.4 # line width
        self.def_layer = 0.2 # layer height
        self.def_speed_print = 40.0 # default printing speed (first layer, etc.)
        self.def_speed_travel = 160.0 # defauld traver speed
        self.def_cooling = 50 # part cooling fan speed (0-100)

    def updatesettings(self, root):
        """
        Method for updating settings from GUI
        """
        self.speed_slow = float(root.speed_slow_entry.get())
        self.speed_fast = float(root.speed_fast_entry.get())
        self.k_start = float(root.speed_fast_start_entry.get())
        self.k_end = float(root.speed_fast_stop_entry.get())
        self.k_step = float(root.speed_fast_step_entry.get())
        self.layers_per_k = int(root.layers_per_k_entry.get())
        self.z_offset = float(root.z_offset_entry.get())
        self.size = (float(root.size_x_entry.get()), float(root.size_y_entry.get()))
        self.retract = (float(root.retract_length_entry.get()), float(root.retract_speed_entry.get()))
        self.bed_size = (float(root.bed_size_x_entry.get()), float(root.bed_size_y_entry.get()))
        self.temperature = (int(root.temperature_hotend_entry.get()), int(root.temperature_bed_entry.get()))
        self.path_spd_fractions = (float(root.path_spd_fractions_slow_entry.get()), float(root.path_spd_fractions_fast_entry.get()),
                              float(root.path_spd_fractions_speeds_entry.get()))
        self.use_G29 = root.use_G29_var.get()
        self.retract_at_layer_change = root.retract_at_layer_change_var.get()
        self.double_perimeter = root.double_perimeter_var.get()

        self.def_fil_dia = float(root.def_fil_dia_entry.get())
        self.def_line_width = float(root.def_line_width_entry.get())
        self.def_layer = float(root.def_layer_entry.get())
        self.def_speed_print = float(root.def_speed_print_entry.get())
        self.def_speed_travel = float(root.def_speed_travel_entry.get())
        self.def_cooling = int(root.def_cooling_entry.get())

    # def update_and_create(self):
    #     self.updatesettings()
    #     creategcode()
    
    def save_config(self, path):
        """
        Method for saving configuration to file
        """
        config = configparser.ConfigParser(allow_no_value=True)
        config.add_section("Config")
        config.set("Config", "# slow speed for calibration pattern")
        config.set("Config", "speed_slow", str(self.speed_slow))

        config.set("Config", "# fast speed for calibrtion pattern")
        config.set("Config", "speed_fast", str(self.speed_fast))

        config.set("Config", "# start values for K-factor calibration")
        config.set("Config", "k_start", str(self.k_start))

        config.set("Config", "# stop values for K-factor calibration")
        config.set("Config", "k_end", str(self.k_end))

        config.set("Config", "# step values for K-factor calibration")
        config.set("Config", "k_step", str(self.k_step))

        config.set("Config", "# number of layers printed with any specific K-factor")
        config.set("Config", "layers_per_k", str(self.layers_per_k))

        config.set("Config", "# Z-offset")
        config.set("Config", "z_offset", str(self.z_offset))

        config.set("Config", "# (X, Y) size of the pattern")
        config.set("Config", "size", str(self.size))

        config.set("Config", "# (length, speed) for retractions")
        config.set("Config", "retract", str(self.retract))

        config.set("Config", "# (X, Y) size of the bed")
        config.set("Config", "bed_size", str(self.bed_size))

        config.set("Config", "# (hotend, bed) temperatures")
        config.set("Config", "temperature", str(self.temperature))

        config.set("Config", "# fractions for pattern parts printed with slow and fast speeds")
        config.set("Config", "path_spd_fractions", str(self.path_spd_fractions))

        config.set("Config", "# adds G29 to start g-code (for autoleveling)")
        config.set("Config", "use_G29", str(self.use_G29))

        config.set("Config", "# retract at layer change")
        config.set("Config", "retract_at_layer_change", str(self.retract_at_layer_change))

        config.set("Config", "# print test with two perimeters instead of one")
        config.set("Config", "double_perimeter", str(self.double_perimeter))

        config.set("Config", "# filament diameter in mm")
        config.set("Config", "def_fil_dia", str(self.def_fil_dia))

        config.set("Config", "# line width")
        config.set("Config", "def_line_width", str(self.def_line_width))

        config.set("Config", "# layer height")
        config.set("Config", "def_layer", str(self.def_layer))

        config.set("Config", "# default printing speed (first layer, etc.)")
        config.set("Config", "def_speed_print", str(self.def_speed_print))

        config.set("Config", "# defauld traver speed")
        config.set("Config", "def_speed_travel", str(self.def_speed_travel))

        config.set("Config", "# part cooling fan speed (0-100%)")
        config.set("Config", "def_cooling", str(self.def_cooling))

        with open(path, "w") as config_file:
            config.write(config_file)
        print("Configuration saved")

    def read_config(self, path):
        """
        Method for reading configuration from file
        """
        config = configparser.ConfigParser()
        config.read(path)
        self.speed_slow = float(config.get("Config", "speed_slow"))
        self.speed_fast = float(config.get("Config", "speed_fast"))
        self.k_start = float(config.get("Config", "k_start"))
        self.k_end = float(config.get("Config", "k_end"))
        self.k_step = float(config.get("Config", "k_step"))
        self.layers_per_k = int(config.get("Config", "layers_per_k"))
        self.z_offset = float(config.get("Config", "z_offset"))
        self.size = tuple(float(v) for v in re.findall("[0-9]+", config.get("Config", "size")))
        self.retract = tuple(float(v) for v in re.findall("[0-9]+", config.get("Config", "retract")))
        self.bed_size = tuple(float(v) for v in re.findall("[0-9]+", config.get("Config", "bed_size")))
        self.temperature = tuple(int(v) for v in re.findall("[0-9]+", config.get("Config", "temperature")))
        self.path_spd_fractions = tuple(float(v) for v in re.findall("[0-9].[0-9]+", config.get("Config", "path_spd_fractions")))
        self.use_G29 = True if "true" in config.get("Config", "use_G29").lower() else False
        self.retract_at_layer_change = True if "true" in config.get("Config", "retract_at_layer_change").lower() else False
        self.double_perimeter = True if "true" in config.get("Config", "double_perimeter").lower() else False

        self.def_fil_dia = float(config.get("Config", "def_fil_dia"))
        self.def_line_width = float(config.get("Config", "def_line_width"))
        self.def_layer = float(config.get("Config", "def_layer"))
        self.def_speed_print = float(config.get("Config", "def_speed_print"))
        self.def_speed_travel = float(config.get("Config", "def_speed_travel"))
        self.def_cooling = int(config.get("Config", "def_cooling"))

        print("Configuration loaded")


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

def M900(k):
    return "M900 K{kf}\nM117 K={kf:.3F}\n".format(kf=k)

def dist(start, end):
    return sqrt((end[0]-start[0])**2+(end[1]-start[1])**2+(end[2]-start[2])**2)


def creategcode(currentConfig):

    print('started creategcode')

    ex = Extruder(0, currentConfig)

    gcode_start = \
    """M190 S{T_b}
M109 S{T_h}
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
G0 Z2 F600
M106 S{C}""".format(T_h=currentConfig.temperature[0], T_b=currentConfig.temperature[1], C=int(currentConfig.def_cooling/100*255), zl=currentConfig.def_layer, zo=currentConfig.def_layer+currentConfig.z_offset, F_t=currentConfig.def_speed_travel*60, F_p=currentConfig.def_speed_print*60, X1=1, Y1=10,
                            Y2=currentConfig.bed_size[1]-10, X2=1+currentConfig.def_line_width, E1=ex.extrude(currentConfig.bed_size[1]-20), E2 = ex.extrude(currentConfig.bed_size[1]-20), G29 = "\nG29" if currentConfig.use_G29 else "")

    gcode_end = \
    """M104 S0
M140 S0
M107
G91
G1 E-{R} F{RS}
G0 Z5 F600
G90
G0 X0 Y0 F{F_t}""".format(R=currentConfig.retract[0], RS = currentConfig.retract[1]*60, F_t = currentConfig.def_speed_travel*60)

    gcode = [gcode_start,]

    #first layer
    ex.e=0
    bed_center = (currentConfig.bed_size[0]/2, currentConfig.bed_size[1]/2)
    current_pos = [1+currentConfig.def_line_width, 10, currentConfig.def_layer]
    # current_e = 0
    layer = []
    for i in range(-5, 5):
        loop = rectangle(currentConfig.bed_size[0]/2, currentConfig.bed_size[1]/2, currentConfig.size[0]+2*i*currentConfig.def_line_width, currentConfig.size[1]+2*i*currentConfig.def_line_width)
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
    corners = rectangle(currentConfig.bed_size[0]/2,currentConfig.bed_size[1]/2, currentConfig.size[0], currentConfig.size[1])
    if currentConfig.double_perimeter:
        
        size2 = (currentConfig.size[0]+2*currentConfig.def_line_width, currentConfig.size[1]+2*currentConfig.def_line_width)
        corners2 = rectangle(currentConfig.bed_size[0]/2,currentConfig.bed_size[1]/2, size2[0], size2[1])
    for k in frange(currentConfig.k_start, currentConfig.k_end+currentConfig.k_step, currentConfig.k_step):
        gcode.append(M900(k))
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
    with open("KF_{b}_{e}_{s}.gcode".format(b=currentConfig.k_start, e=currentConfig.k_end, s=currentConfig.k_step), "w") as out:
        out.writelines(gcode)
    print('stopped creategcode')


# Validation
def validate(string):
    """
    Validation function.
    Allows to enter only floating point numbers
    """
    regex = re.compile(r"(\+|\-)?[0-9.]*$")
    result = regex.match(string)
    return (string == ""
            or (string.count('+') <= 1
                and string.count('-') <= 1
                and string.count('.') <= 1
                and result is not None
                and result.group(0) != ""))

def on_validate(P):
    return validate(P)


# dimensions of the outer border (border) grid horizontally and vertically.
padx = 4
pady = 1

def create_entry(root, width=50):
    """
    Entry binding function to validation.
    """
    new_entry = ttk.Entry(root, width=width, validate="key")
    vcmd = (new_entry.register(on_validate), '%P')
    new_entry.config(validatecommand=vcmd)
    return new_entry

def create_interfase(root, lb_text, lb_row, lb_col, ent_row, ent_col, padx = padx, pady = pady, insert = ''):
    """
    Lebel and entry creation function
    """
    new_lable = ttk.Label(root, text=lb_text)
    new_lable.grid(row=lb_row, column=lb_col, columnspan=1, sticky='w', padx=padx, pady=pady)
    new_entry = (create_entry(root))
    new_entry.grid(row=ent_row, column=ent_col, columnspan=1, sticky='w', padx=padx, pady=pady)
    new_entry.insert(0, str(insert))
    return new_lable, new_entry

class Main:
    def __init__(self, root = None, currentConfig = None):
        _bgcolor = '#d9d9d9'  # X11 color: 'gray85'
        _fgcolor = '#000000'  # X11 color: 'black'
        _compcolor = '#d9d9d9' # X11 color: 'gray85'
        _ana1color = '#d9d9d9' # X11 color: 'gray85'
        _ana2color = '#ececec' # Closest X11 color: 'gray92'
        self.style = ttk.Style()
        if sys.platform == "win32":
            self.style.theme_use('winnative')
        self.style.configure('.',background=_bgcolor)
        self.style.configure('.',foreground=_fgcolor)
        self.style.configure('.',font="TkDefaultFont")
        self.style.map('.',background=
            [('selected', _compcolor), ('active',_ana2color)])
        
        root.geometry('635x570+300+200')
        root.minsize(635, 570)
        root.maxsize(635, 570)
        root.resizable(0, 0)
        root.title("Kcalibrator - alternative K-factor calibration pattern")
        root.configure(background="#d9d9d9")

        # slow speed for calibration pattern
        self.speed_slow_lable, self.speed_slow_entry  = create_interfase(root,
                                                                  u'Slow speed for calibration pattern, mm/s',
                                                                  1, 1, 2, 1, insert=currentConfig.speed_slow)
        # fast speed for calibrtion pattern
        self.speed_fast_lable, self.speed_fast_entry = create_interfase(root,
                                                                  u'Fast speed for calibration pattern mm/s',
                                                                  3, 1, 4, 1, insert=currentConfig.speed_fast)
        # Start, stop and step values for K-factor calibration
        self.speed_fast_lable = ttk.Label(root, text=u'Start, stop and step values for K-factor calibration')
        self.speed_fast_lable.grid(row=5, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.speed_fast_start_entry = (create_entry(root))
        self.speed_fast_start_entry.grid(row=6, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.speed_fast_start_entry.insert(1, str(currentConfig.k_start))
        self.speed_fast_stop_entry = (create_entry(root))
        self.speed_fast_stop_entry.grid(row=7, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.speed_fast_stop_entry.insert(1, str(currentConfig.k_end))
        self.speed_fast_step_entry = (create_entry(root))
        self.speed_fast_step_entry.grid(row=8, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.speed_fast_step_entry.insert(1, str(currentConfig.k_step))
        # number of layers printed with any specific K-factor
        self.layers_per_k_lable, self.layers_per_k_entry = create_interfase(root,
                                                                  u'Number of layers printed with any specific K-factor',
                                                                  9, 1, 10, 1, insert=currentConfig.layers_per_k)
        # Z-offset
        self.z_offset_lable, self.z_offset_entry = create_interfase(root,
                                                                  u'Z-offset, mm',
                                                                  11, 1, 12, 1, insert=currentConfig.z_offset)
        # (X, Y) size of the pattern
        self.size_lable = ttk.Label(root, text=u'X and Y size of the pattern, mm')
        self.size_lable.grid(row=13, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.size_x_entry = (create_entry(root))
        self.size_x_entry.grid(row=14, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.size_x_entry.insert(1, str(currentConfig.size[0]))
        self.size_y_entry = (create_entry(root))
        self.size_y_entry.grid(row=15, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.size_y_entry.insert(1, str(currentConfig.size[1]))
        # (length, speed) for retractions
        self.retract_lable = ttk.Label(root, text=u'Distance and speed for retractions, mm and mm/s')
        self.retract_lable.grid(row=16, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.retract_length_entry = (create_entry(root))
        self.retract_length_entry.grid(row=17, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.retract_length_entry.insert(1, str(currentConfig.retract[0]))
        self.retract_speed_entry = (create_entry(root))
        self.retract_speed_entry.grid(row=18, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.retract_speed_entry.insert(1, str(currentConfig.retract[1]))
        # (X, Y) size of the bed
        self.bed_size_lable = ttk.Label(root, text=u'X and Y size of the printbed, mm')
        self.bed_size_lable.grid(row=19, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.bed_size_x_entry = (create_entry(root))
        self.bed_size_x_entry.grid(row=20, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.bed_size_x_entry.insert(1, str(currentConfig.bed_size[0]))
        self.bed_size_y_entry = (create_entry(root))
        self.bed_size_y_entry.grid(row=21, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.bed_size_y_entry.insert(1, str(currentConfig.bed_size[1]))
        # (hotend, bed) temperatures
        self.temperature_lable = ttk.Label(root, text=u'Hotend and printbed temperature')
        self.temperature_lable.grid(row=1, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.temperature_hotend_entry = (create_entry(root))
        self.temperature_hotend_entry.grid(row=2, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.temperature_hotend_entry.insert(1, str(currentConfig.temperature[0]))
        self.temperature_bed_entry = (create_entry(root))
        self.temperature_bed_entry.grid(row=3, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.temperature_bed_entry.insert(1, str(currentConfig.temperature[1]))
        # fractions for pattern parts printed with slow and fast speeds
        self.path_spd_fractions_lable = ttk.Label(root, text=u'Fractions for pattern paths')
        self.path_spd_fractions_lable.grid(row=4, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.path_spd_fractions_slow_entry = (create_entry(root))
        self.path_spd_fractions_slow_entry.grid(row=5, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.path_spd_fractions_slow_entry.insert(1, str(currentConfig.path_spd_fractions[0]))
        self.path_spd_fractions_fast_entry = (create_entry(root))
        self.path_spd_fractions_fast_entry.grid(row=6, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.path_spd_fractions_fast_entry.insert(1, str(currentConfig.path_spd_fractions[1]))
        self.path_spd_fractions_speeds_entry = (create_entry(root))
        self.path_spd_fractions_speeds_entry.grid(row=7, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        self.path_spd_fractions_speeds_entry.insert(1, str(currentConfig.path_spd_fractions[2]))
        # adds G29 to start g-code (for autoleveling)
        self.use_G29_var = tk.BooleanVar()
        self.use_G29_var.set(currentConfig.use_G29)
        self.use_G29_checkbutton = ttk.Checkbutton(root, text=u'Use autoleveling (adds G29)',
                                             variable=self.use_G29_var, onvalue=True, offvalue=False)
        # self.use_G29_checkbutton.select() if self.use_G29_var.get() else self.use_G29_checkbutton.deselect()
        self.use_G29_checkbutton.grid(row=8, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        # retract at layer change
        self.retract_at_layer_change_var = tk.BooleanVar()
        self.retract_at_layer_change_var.set(currentConfig.retract_at_layer_change)
        self.retract_at_layer_change_checkbutton = ttk.Checkbutton(root, text=u'Retract at layer change',
                                             variable=self.retract_at_layer_change_var, onvalue=True, offvalue=False)
        self.retract_at_layer_change_checkbutton.grid(row=9, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        # print test with two perimeters instead of one
        self.double_perimeter_var = tk.BooleanVar()
        self.double_perimeter_var.set(currentConfig.double_perimeter)
        self.double_perimeter_checkbutton = ttk.Checkbutton(root, text=u'Print test with two perimeters instead of one',
                                             variable=self.double_perimeter_var, onvalue=True, offvalue=False)
        self.double_perimeter_checkbutton.grid(row=10, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        # filament diameter in mm
        self.def_fil_dia_lable, self.def_fil_dia_entry  = create_interfase(root,
                                                                  u'Filament diameter, mm',
                                                                  11, 2, 12, 2, insert=currentConfig.def_fil_dia)
        # line width
        self.def_line_width_lable, self.def_line_width_entry  = create_interfase(root,
                                                                  u'Line width, mm',
                                                                  13, 2, 14, 2, insert=currentConfig.def_line_width)
        # layer height
        self.def_layer_lable, self.def_layer_entry  = create_interfase(root,
                                                                  u'Layer height, mm',
                                                                  15, 2, 16, 2, insert=currentConfig.def_layer)
        # default printing speed (first layer, etc.)
        self.def_speed_print_lable, self.def_speed_print_entry  = create_interfase(root,
                                                                  u'Default printing speed (first layer, etc.), mm/s',
                                                                  17, 2, 18, 2, insert=currentConfig.def_speed_print)
        # defauld travel speed
        self.def_speed_travel_lable, self.def_speed_travel_entry  = create_interfase(root,
                                                                  u'Defauld travel speed, mm/s',
                                                                  19, 2, 20, 2, insert=currentConfig.def_speed_travel)
        # part cooling fan speed (0-100%)
        self.def_cooling_lable, self.def_cooling_entry  = create_interfase(root,
                                                                  u'Part cooling fan speed (0-100%)',
                                                                  21, 2, 22, 2, insert=currentConfig.def_cooling)
        # creating a button
        button1 = ttk.Button(root, text=u"Generate gcode", command=update_and_create)
        button1.grid(row=23, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
        # creating a button
        button2 = ttk.Button(root, text=u"Save config", command=def_save_config)
        button2.grid(row=23, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)


def gui_init(top, gui, *args, **kwargs):
    global w, top_level, root
    w = gui
    top_level = top
    root = top

def gui_destroy_window():
    # Function which closes the window.
    global top_level
    top_level.destroy()
    top_level = None

def def_save_config():
    global currentConfig, top
    currentConfig.updatesettings(top)
    currentConfig.save_config(configPath)

def update_and_create():
    global currentConfig, top
    currentConfig.updatesettings(top)
    creategcode(currentConfig)

configPath = "Kcalibrator.cfg"
currentConfig = SettingClass()

if os.path.exists(configPath):
    currentConfig.read_config(configPath)
else:
    currentConfig.save_config(configPath)

root = tk.Tk()
top = Main(root, currentConfig)
gui_init(root, top)

root.mainloop()