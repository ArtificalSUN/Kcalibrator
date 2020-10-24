#!python3
# coding: utf-8
# author: Victor Shapovalov (@ArtificalSUN), 2020
# version: 0.2.0


"""
this script generates pattern fot Linear Advance K-factor calibration for Marlin (and other firmwares which use M900 to adjust pressure control algorithms)
the pattern consists of a rectangular wall printed with sharp changes in speed and with K-factor increasing from bottom to top
print the pattern and find the height where it looks the best
corners should not bulge, flow should be homogeneous with as little influence from speed changes as possible, seam should be barely noticeable
calculate desired K-factor from this height and parameters u used to generate the pattern
good luck
"""

import os, sys, re, configparser
from math import pi, sqrt
import tkinter as tk

class SettingClass():
    """
    this class stores all the variable generation settings for gcode
    """
    def __init__(self):
        self.speed_slow = 20 # slow speed for calibration pattern
        self.speed_fast = 90 # fast speed for calibrtion pattern
        self.k_start = 0.2 # \
        self.k_end = 0.6   # | start, stop and step values for K-factor calibration
        self.k_step = 0.02 # /
        self.layers_per_k = 5 # number of layers printed with any specific K-factor
        self.z_offset=0.16 # Z-offset
        self.size = (120, 60) # (X, Y) size of the pattern
        self.retract = (4, 30) # (length, speed) for retractions
        self.bed_size = (235,180) # (X, Y) size of the bed
        self.temperature = (250,80) # (hotend, bed) temperatures
        self.path_spd_fractions = (0.2, 0.6, 0.2) #fractions for pattern parts printed with slow and fast speeds
        self.use_G29 = False # adds G29 to start g-code (for autoleveling)
        self.retract_at_layer_change = False # retract at layer change
        self.double_perimeter = False # print test with two perimeters instead of one

        self.def_fil_dia = 1.75 # filament diameter in mm
        self.def_line_width = 0.5 # line width
        self.def_layer = 0.2 # layer height
        self.def_speed_print = 60 # default printing speed (first layer, etc.)
        self.def_speed_travel = 160 # defauld traver speed
        self.def_cooling = 127 # part cooling fan speed (0-255)

    def updatesettings(self):
        """
        method for updating variables variable a form
        """
        self.speed_slow = int(speed_slow_entry.get())
        self.speed_fast = int(speed_fast_entry.get())
        self.k_start = float(speed_fast_start_entry.get())
        self.k_end = float(speed_fast_stop_entry.get())
        self.k_step = float(speed_fast_step_entry.get())
        self.layers_per_k = int(layers_per_k_entry.get())
        self.z_offset = float(z_offset_entry.get())
        self.size = (int(size_x_entry.get()), int(size_y_entry.get()))
        self.retract = (int(retract_length_entry.get()), int(retract_speed_entry.get()))
        self.bed_size = (int(bed_size_x_entry.get()), int(bed_size_y_entry.get()))
        self.temperature = (int(temperature_hotend_entry.get()), int(temperature_bed_entry.get()))
        self.path_spd_fractions = (float(path_spd_fractions_slow_entry.get()), float(path_spd_fractions_fast_entry.get()),
                              float(path_spd_fractions_speeds_entry.get()))
        self.use_G29 = use_G29_var.get()
        self.retract_at_layer_change = retract_at_layer_change_var.get()
        self.double_perimeter = double_perimeter_var.get()

        self.def_fil_dia = float(def_fil_dia_entry.get())
        self.def_line_width = float(def_line_width_entry.get())
        self.def_layer = float(def_layer_entry.get())
        self.def_speed_print = int(def_speed_print_entry.get())
        self.def_speed_travel = int(def_speed_print_entry.get())
        self.def_cooling = int(def_cooling_entry.get())

    def update_and_create(self):

        self.updatesettings()
        creategcode()
    
    def save_config(self, path):
        """
        Save a config file
        """

        self.updatesettings()

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

        config.set("Config", "# part cooling fan speed (0-255)")
        config.set("Config", "def_cooling", str(self.def_cooling))

        with open(path, "w") as config_file:
            config.write(config_file)
        
        print("save config")
    
    def read_config(self, path):
        
        """
        Read a config file
        """
        config = configparser.ConfigParser()
        config.read(path)
        self.speed_slow = int(config.get("Config", "speed_slow"))
        self.speed_fast = int(config.get("Config", "speed_fast"))
        self.k_start = float(config.get("Config", "k_start"))
        self.k_end = float(config.get("Config", "k_end"))
        self.k_step = float(config.get("Config", "k_step"))
        self.layers_per_k = int(config.get("Config", "layers_per_k"))
        self.z_offset = float(config.get("Config", "z_offset"))
        self.size = tuple(int(v) for v in re.findall("[0-9]+", config.get("Config", "size")))
        self.retract = tuple(int(v) for v in re.findall("[0-9]+", config.get("Config", "retract")))
        self.bed_size = tuple(int(v) for v in re.findall("[0-9]+", config.get("Config", "bed_size")))
        self.temperature = tuple(int(v) for v in re.findall("[0-9]+", config.get("Config", "temperature")))
        self.path_spd_fractions = tuple(float(v) for v in re.findall("[0-9].[0-9]+", config.get("Config", "path_spd_fractions")))
        self.use_G29 = True if "True" in config.get("Config", "use_G29") else False
        self.retract_at_layer_change = True if "True" in config.get("Config", "retract_at_layer_change") else False
        self.double_perimeter = True if "True" in config.get("Config", "double_perimeter") else False

        self.def_fil_dia = float(config.get("Config", "def_fil_dia"))
        self.def_line_width = float(config.get("Config", "def_line_width"))
        self.def_layer = float(config.get("Config", "def_layer"))
        self.def_speed_print = int(config.get("Config", "def_speed_print"))
        self.def_speed_travel = int(config.get("Config", "def_speed_travel"))
        self.def_cooling = int(config.get("Config", "def_cooling"))
        
        print("read config")
    
path = "Config.ini"
mainsettting = SettingClass()

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
    def extrude(self, l, w=mainsettting.def_line_width, h=mainsettting.def_layer, flow=1.0, dia = mainsettting.def_fil_dia):
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


def creategcode():

    print('starting creategcode')

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
    G0 Z2 F600""".format(T_h=mainsettting.temperature[0], T_b=mainsettting.temperature[1], C=mainsettting.def_cooling, zl=mainsettting.def_layer, zo=mainsettting.def_layer+mainsettting.z_offset, F_t=mainsettting.def_speed_travel*60, F_p=mainsettting.def_speed_print*60, X1=1, Y1=10,
                            Y2=mainsettting.bed_size[1]-10, X2=1+mainsettting.def_line_width, E1=ex.extrude(mainsettting.bed_size[1]-20), E2 = ex.extrude(mainsettting.bed_size[1]-20), G29 = "\nG29" if mainsettting.use_G29 else "")

    gcode_end = \
    """M104 S0
    M140 S0
    M107
    G91
    G1 E-{R} F{RS}
    G0 Z5 F600
    G90
    G0 X0 Y0 F{F_t}""".format(R=mainsettting.retract[0], RS = mainsettting.retract[1]*60, F_t = mainsettting.def_speed_travel*60)

    gcode = [gcode_start,]

    #first layer
    ex.e=0
    bed_center = (mainsettting.bed_size[0]/2, mainsettting.bed_size[1]/2)
    current_pos = [1+mainsettting.def_line_width, 10, mainsettting.def_layer]
    # current_e = 0
    layer = []
    for i in range(-5, 5):
        loop = rectangle(mainsettting.bed_size[0]/2, mainsettting.bed_size[1]/2, mainsettting.size[0]+2*i*mainsettting.def_line_width, mainsettting.size[1]+2*i*mainsettting.def_line_width)
        next_pos = moveabs(current_pos, loop[3][0], loop[3][1])
        layer.append(G0(next_pos, mainsettting.def_speed_travel))
        current_pos = next_pos[:]
        for point in loop:
            next_pos = moveabs(current_pos, point[0], point[1])
            # next_e = ex.extrude(dist(current_pos, next_pos))
            layer.append(G1(next_pos, ex.extrude(dist(current_pos, next_pos)), mainsettting.def_speed_print))
            current_pos = next_pos[:]
            # current_e += next_e
    gcode.extend(layer)
    gcode.extend(["G92 E0\n",
                "G1 E-{R} F{S}\n".format(R=mainsettting.retract[0], S=mainsettting.retract[1]*60) if mainsettting.retract_at_layer_change else ""])

    #pattern generation
    current_z = current_pos[2]
    corners = rectangle(mainsettting.bed_size[0]/2,mainsettting.bed_size[1]/2, mainsettting.size[0], mainsettting.size[1])
    if mainsettting.double_perimeter:
        
        size2 = (mainsettting.size[0]+2*mainsettting.def_line_width, mainsettting.size[1]+2*mainsettting.def_line_width)
        corners2 = rectangle(mainsettting.bed_size[0]/2,mainsettting.bed_size[1]/2, size2[0], size2[1])
    for k in frange(mainsettting.k_start, mainsettting.k_end+mainsettting.k_step, mainsettting.k_step):
        gcode.append(M900(k))
        for i in range(mainsettting.layers_per_k):
            current_z+=mainsettting.def_layer
            layer = []
            ex.e = 0
            layer.extend([G0((bed_center[0], bed_center[1]+mainsettting.size[1]/2, current_z), mainsettting.def_speed_travel),
                        "G1 E0 F{S}\n".format(S=mainsettting.retract[1]*60) if mainsettting.retract_at_layer_change else "",
                        G1((corners[1][0]+mainsettting.size[0]*mainsettting.path_spd_fractions[0], corners[1][1], current_z), ex.extrude(abs(corners[1][0]+mainsettting.size[0]*mainsettting.path_spd_fractions[0]-bed_center[0])), mainsettting.speed_slow),
                        G1((corners[1][0], corners[1][1], current_z), ex.extrude(abs(mainsettting.size[0]*mainsettting.path_spd_fractions[2])), mainsettting.speed_fast),
                        G1((corners[1][0], corners[0][1]+mainsettting.size[1]/2, current_z), ex.extrude(abs(mainsettting.size[1]/2)), mainsettting.speed_fast),
                        G1((corners[0][0], corners[0][1], current_z), ex.extrude(abs(mainsettting.size[1]/2)), mainsettting.speed_slow),
                        G1((corners[0][0]+mainsettting.size[0]*mainsettting.path_spd_fractions[0], corners[0][1], current_z), ex.extrude(abs(mainsettting.size[0]*mainsettting.path_spd_fractions[0])), mainsettting.speed_slow),
                        G1((corners[3][0]-mainsettting.size[0]*(mainsettting.path_spd_fractions[2]), corners[0][1], current_z), ex.extrude(abs(mainsettting.size[0]*mainsettting.path_spd_fractions[1])), mainsettting.speed_fast),
                        G1((corners[3][0], corners[3][1], current_z), ex.extrude(abs(mainsettting.size[0]*mainsettting.path_spd_fractions[2])), mainsettting.speed_slow),
                        G1((corners[3][0], corners[3][1]+mainsettting.size[1]/2, current_z), ex.extrude(abs(mainsettting.size[1]/2)), mainsettting.speed_slow),
                        G1((corners[2][0], corners[2][1], current_z), ex.extrude(abs(mainsettting.size[1]/2)), mainsettting.speed_fast),
                        G1((corners[2][0]-mainsettting.size[0]*mainsettting.path_spd_fractions[2], corners[2][1], current_z), ex.extrude(abs(mainsettting.size[0]*mainsettting.path_spd_fractions[2])), mainsettting.speed_fast),
                        G1((bed_center[0]+mainsettting.def_line_width/2, bed_center[1]+mainsettting.size[1]/2, current_z), ex.extrude(abs(bed_center[0]+mainsettting.def_line_width/2-corners[2][0])), mainsettting.speed_slow),
                        "G92 E0\n",
                        "G1 E-{R} F{S}\n".format(R=mainsettting.retract[0], S=mainsettting.retract[1]*60) if (mainsettting.retract_at_layer_change and not mainsettting.double_perimeter) else ""])
            current_pos = (bed_center[0]+mainsettting.def_line_width/2, bed_center[1]+mainsettting.size[1]/2, current_z)

            if mainsettting.double_perimeter:
                ex.e = 0
                layer.extend([G0((bed_center[0], bed_center[1]+size2[1]/2, current_z), mainsettting.def_speed_travel),
                            "G1 E0 F{S}\n".format(S=mainsettting.retract[1]*60) if (mainsettting.retract_at_layer_change and not mainsettting.double_perimeter) else "",
                            G1((corners2[1][0]+size2[0]*mainsettting.path_spd_fractions[0], corners2[1][1], current_z), ex.extrude(abs(corners2[1][0]+size2[0]*mainsettting.path_spd_fractions[0]-bed_center[0])), mainsettting.speed_slow),
                            G1((corners2[1][0], corners2[1][1], current_z), ex.extrude(abs(size2[0]*mainsettting.path_spd_fractions[2])), mainsettting.speed_fast),
                            G1((corners2[1][0], corners2[0][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), mainsettting.speed_fast),
                            G1((corners2[0][0], corners2[0][1], current_z), ex.extrude(abs(size2[1]/2)), mainsettting.speed_slow),
                            G1((corners2[0][0]+size2[0]*mainsettting.path_spd_fractions[0], corners2[0][1], current_z), ex.extrude(abs(size2[0]*mainsettting.path_spd_fractions[0])), mainsettting.speed_slow),
                            G1((corners2[3][0]-size2[0]*(mainsettting.path_spd_fractions[2]), corners2[0][1], current_z), ex.extrude(abs(size2[0]*mainsettting.path_spd_fractions[1])), mainsettting.speed_fast),
                            G1((corners2[3][0], corners2[3][1], current_z), ex.extrude(abs(size2[0]*mainsettting.path_spd_fractions[2])), mainsettting.speed_slow),
                            G1((corners2[3][0], corners2[3][1]+size2[1]/2, current_z), ex.extrude(abs(size2[1]/2)), mainsettting.speed_slow),
                            G1((corners2[2][0], corners2[2][1], current_z), ex.extrude(abs(size2[1]/2)), mainsettting.speed_fast),
                            G1((corners2[2][0]-size2[0]*mainsettting.path_spd_fractions[2], corners2[2][1], current_z), ex.extrude(abs(size2[0]*mainsettting.path_spd_fractions[2])), mainsettting.speed_fast),
                            G1((bed_center[0]+mainsettting.def_line_width/2, bed_center[1]+size2[1]/2, current_z), ex.extrude(abs(bed_center[0]+mainsettting.def_line_width/2-corners2[2][0])), mainsettting.speed_slow),
                            "G92 E0\n",
                            "G1 E-{R} F{S}\n".format(R=mainsettting.retract[0], S=mainsettting.retract[1]*60) if mainsettting.retract_at_layer_change else ""])
                current_pos = (bed_center[0]+mainsettting.def_line_width/2, bed_center[1]+size2[1]/2, current_z)
            gcode.extend(layer)

    gcode.append(gcode_end)
    with open("KF_{b}_{e}_{s}.gcode".format(b=mainsettting.k_start, e=mainsettting.k_end, s=mainsettting.k_step), "w") as out:
        out.writelines(gcode)
    print('stoped creategcode')


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


def creature_entry(root, width=50):
    """
    Entry binding function to validation.
    """
    new_entry = tk.Entry(root, borderwidth=2, width=width, validate="key")
    vcmd = (new_entry.register(on_validate), '%P')
    new_entry.config(validatecommand=vcmd)
    return new_entry

def create_interfase(root, ltest, lrow, lckumn, erow, eclumn, padx = 2, pady = 2, insert = ''):
    """
    Lebel and entry creation function
    """
    new_lable = tk.Label(root, text=ltest)
    new_lable.grid(row=lrow, column=lckumn, columnspan=1, sticky='w', padx=padx, pady=pady)
    new_entry = (creature_entry(root))
    new_entry.grid(row=erow, column=eclumn, columnspan=1, sticky='w', padx=padx, pady=pady)
    new_entry.insert(0, str(insert))
    return new_lable, new_entry


# the dimensions of the outer border (border) grid horizontally and vertically.
padx = 2
pady = 2

if os.path.exists(path):
    mainsettting.read_config(path)
else:
    mainsettting.save_config(path)


# window initialization
root = tk.Tk()
root.title('Kcalibrator')
root.geometry('630x600+300+200')
root.resizable(False, True)

# slow speed for calibration pattern
speed_slow_lable, speed_slow_entry  = create_interfase(root,
                                                          u'Slow speed for calibration pattern',
                                                          1, 1, 2, 1, insert=mainsettting.speed_slow)

# fast speed for calibrtion pattern
speed_fast_lable, speed_fast_entry = create_interfase(root,
                                                          u'Fast speed for calibrtion pattern',
                                                          3, 1, 4, 1, insert=mainsettting.speed_fast)

# Start, stop and step values for K-factor calibration
speed_fast_lable = tk.Label(root, text=u'Start, stop and step values for K-factor calibration')
speed_fast_lable.grid(row=5, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
speed_fast_start_entry = (creature_entry(root))
speed_fast_start_entry.grid(row=6, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
speed_fast_start_entry.insert(1, str(mainsettting.k_start))
speed_fast_stop_entry = (creature_entry(root))
speed_fast_stop_entry.grid(row=7, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
speed_fast_stop_entry.insert(1, str(mainsettting.k_end))
speed_fast_step_entry = (creature_entry(root))
speed_fast_step_entry.grid(row=8, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
speed_fast_step_entry.insert(1, str(mainsettting.k_step))

# number of layers printed with any specific K-factor
layers_per_k_lable, layers_per_k_entry = create_interfase(root,
                                                          u'Number of layers printed with any specific K-factor',
                                                          9, 1, 10, 1, insert=mainsettting.layers_per_k)

# Z-offset

z_offset_lable, z_offset_entry = create_interfase(root,
                                                          u'Z-offset',
                                                          11, 1, 12, 1, insert=mainsettting.z_offset)
# (X, Y) size of the pattern
size_lable = tk.Label(root, text=u'(X, Y) size of the pattern')
size_lable.grid(row=13, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
size_x_entry = (creature_entry(root))
size_x_entry.grid(row=14, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
size_x_entry.insert(1, str(mainsettting.size[0]))
size_y_entry = (creature_entry(root))
size_y_entry.grid(row=15, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
size_y_entry.insert(1, str(mainsettting.size[1]))

# (length, speed) for retractions
retract_lable = tk.Label(root, text=u'(length, speed) for retractions')
retract_lable.grid(row=16, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
retract_length_entry = (creature_entry(root))
retract_length_entry.grid(row=17, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
retract_length_entry.insert(1, str(mainsettting.retract[0]))
retract_speed_entry = (creature_entry(root))
retract_speed_entry.grid(row=18, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
retract_speed_entry.insert(1, str(mainsettting.retract[1]))

# (X, Y) size of the bed
bed_size_lable = tk.Label(root, text=u'(length, speed) for retractions')
bed_size_lable.grid(row=19, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
bed_size_x_entry = (creature_entry(root))
bed_size_x_entry.grid(row=20, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
bed_size_x_entry.insert(1, str(mainsettting.bed_size[0]))
bed_size_y_entry = (creature_entry(root))
bed_size_y_entry.grid(row=21, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)
bed_size_y_entry.insert(1, str(mainsettting.bed_size[1]))

# (hotend, bed) temperatures
temperature_lable = tk.Label(root, text=u'(Hotend, bed) temperatures')
temperature_lable.grid(row=1, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
temperature_hotend_entry = (creature_entry(root))
temperature_hotend_entry.grid(row=2, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
temperature_hotend_entry.insert(1, str(mainsettting.temperature[0]))
temperature_bed_entry = (creature_entry(root))
temperature_bed_entry.grid(row=3, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
temperature_bed_entry.insert(1, str(mainsettting.temperature[1]))

# fractions for pattern parts printed with slow and fast speeds
path_spd_fractions_lable = tk.Label(root, text=u'(Hotend, bed) temperatures')
path_spd_fractions_lable.grid(row=4, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
path_spd_fractions_slow_entry = (creature_entry(root))
path_spd_fractions_slow_entry.grid(row=5, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
path_spd_fractions_slow_entry.insert(1, str(mainsettting.path_spd_fractions[0]))
path_spd_fractions_fast_entry = (creature_entry(root))
path_spd_fractions_fast_entry.grid(row=6, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
path_spd_fractions_fast_entry.insert(1, str(mainsettting.path_spd_fractions[1]))
path_spd_fractions_speeds_entry = (creature_entry(root))
path_spd_fractions_speeds_entry.grid(row=7, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)
path_spd_fractions_speeds_entry.insert(1, str(mainsettting.path_spd_fractions[2]))

# adds G29 to start g-code (for autoleveling)
use_G29_var = tk.BooleanVar()
use_G29_var.set(mainsettting.use_G29)
use_G29_checkbutton = tk.Checkbutton(root, text=u'Adds G29 to start g-code (for autoleveling)',
                                     variable=use_G29_var, onvalue=True, offvalue=False)   
use_G29_checkbutton.select() if use_G29_var.get() else use_G29_checkbutton.deselect()
use_G29_checkbutton.grid(row=8, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)

# retract at layer change
retract_at_layer_change_var = tk.BooleanVar()
retract_at_layer_change_var.set(mainsettting.retract_at_layer_change)
retract_at_layer_change_checkbutton = tk.Checkbutton(root, text=u'Retract at layer change',
                                     variable=retract_at_layer_change_var, onvalue=True, offvalue=False)
retract_at_layer_change_checkbutton.grid(row=9, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)

# print test with two perimeters instead of one
double_perimeter_var = tk.BooleanVar()
double_perimeter_var.set(mainsettting.double_perimeter)
double_perimeter_checkbutton = tk.Checkbutton(root, text=u'Print test with two perimeters instead of one',
                                     variable=double_perimeter_var, onvalue=True, offvalue=False)
double_perimeter_checkbutton.grid(row=10, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)

# filament diameter in mm
def_fil_dia_lable, def_fil_dia_entry  = create_interfase(root,
                                                          u'Filament diameter in mm',
                                                          11, 2, 12, 2, insert=mainsettting.def_fil_dia)
# line width
def_line_width_lable, def_line_width_entry  = create_interfase(root,
                                                          u'Line width',
                                                          13, 2, 14, 2, insert=mainsettting.def_line_width)

# layer height
def_layer_lable, def_layer_entry  = create_interfase(root,
                                                          u'Layer height',
                                                          15, 2, 16, 2, insert=mainsettting.def_layer)

# default printing speed (first layer, etc.)
def_speed_print_lable, def_speed_print_entry  = create_interfase(root,
                                                          u'Default printing speed (first layer, etc.)',
                                                          17, 2, 18, 2, insert=mainsettting.def_speed_print)

# defauld traver speed
def_speed_print_lable, def_speed_print_entry  = create_interfase(root,
                                                          u'Ddefauld traver speed',
                                                          19, 2, 20, 2, insert=mainsettting.def_speed_travel)

# part cooling fan speed (0-255)
def_cooling_lable, def_cooling_entry  = create_interfase(root,
                                                          u'Part cooling fan speed (0-255)',
                                                          21, 2, 22, 2, insert=mainsettting.def_cooling)


def def_save_config():
    mainsettting.save_config(path)

# creating a button
button1 = tk.Button(root, text=u"Generate gcode", command=mainsettting.update_and_create)
button1.grid(row=23, column=2, columnspan=1, sticky='w', padx=padx, pady=pady)

# creating a button
button2 = tk.Button(root, text=u"Save config", command=def_save_config)
button2.grid(row=23, column=1, columnspan=1, sticky='w', padx=padx, pady=pady)


root.mainloop()