#! /usr/bin/env python
#  -*- coding: utf-8 -*-
# author: Victor Shapovalov (@ArtificalSUN, https://github.com/ArtificalSUN), 2022
# Configuration contributed by Foreytor (https://github.com/Foreytor)
# version: 1.0.4-bugfix

"""
This script generates pattern for Linear Advance
K-factor calibration for Marlin (and other firmwares).
The pattern consists of a rectangular wall printed with sharp
changes in speed and with K-factor increasing from bottom to top.
Print the pattern and find the height where it looks the best.
Corners should not bulge, flow should be homogeneous with as little
influence from speed changes as possible, seam should be barely noticeable.
Calculate desired K-factor from this height and parameters
you used to generate the pattern.
Good luck!
"""

import sys
import tkinter as tk
import tkinter.filedialog as fldg
import tkinter.messagebox as mbx

import kcalibrator_gui as gui
import kcalibrator_gui_support as gui_support
import kcalibrator_settings as settings
from gcode import creategcode


class Application:
    def __init__(self):
        self.version = "Kcalibrator v1.0.4-bugfix (Victor Shapovalov, 2022)"
        self.configPath = "Kcalibrator.cfg"
        self.configStorage = None
        self.root = None
        self.ui = None

    def create_profile(self):
        w = gui.TextDialog(self.root)
        self.root.wait_window(w.top)
        name = w.value

        if not name:
            return

        profiles = self.configStorage.get_profiles_list()
        if name in profiles:
            mbx.showerror("Already exists", "Profile \"{}\" already exists".format(name))
            return

        profile = settings.SettingsProfile(name)
        self.configStorage.add_profile(profile)
        self.configStorage.set_profile(name)
        self.on_profile_list_changed()

    def delete_profile(self):
        current = self.configStorage.current.name
        message = "Delete profile \"{}\"?".format(current)
        result = mbx.askquestion("Delete profile", message, icon='warning')
        if result.lower() == "yes":
            self.configStorage.delete_profile(current)
            self.on_profile_list_changed()

    def change_profile(self):
        profile = self.ui.cmb_CurrProfile_var.get()
        if profile == self.configStorage.current.name:
            return

        print("[main] Selected profile: {}".format(profile))
        self.configStorage.set_profile(profile)
        self.ui.updateUI(self.configStorage.current)

    def on_profile_list_changed(self):
        self.ui.set_profile_list(self.configStorage.get_profiles_list())
        self.ui.updateUI(self.configStorage.current)

    def save_config(self):
        self.configStorage.current.update(self.ui)
        self.configStorage.save_config()

    def update_and_create(self):
        self.configStorage.current.update(self.ui)

        config = self.configStorage.current
        dfn = "KF_{b}-{e}-{s}_H{t[0]}-B{t[1]}.gcode"
        file_name = dfn.format(
            b=config.k_start, e=config.k_end,
            s=config.k_step, t=config.temperature)
        path = fldg.asksaveasfilename(
            title="Save the G-code", defaultextension=".gcode", initialfile=file_name,
            filetypes=(("G-code files", "*.gcode"), ("All files", "*.*")))

        if not path:
            print('[main] File save cancelled')
            return

        gcode = creategcode(config, self.version)
        with open(path, "w") as out:
            out.writelines(gcode)

    def run(self):
        self.configStorage = settings.SettingClass(self.configPath)
        self.configStorage.try_load()

        self.root = tk.Tk()
        print("[main] Running with Python {}".format(sys.version))
        print("[main] Tkinter Tcl/Tk version {}".format(
            self.root.tk.call("info", "patchlevel")))
        gui_support.set_Tk_var()
        self.ui = gui.Toplevel(self.root)
        gui_support.init(self.root, self.ui)
        self.ui.attach()

        try:
            self.on_profile_list_changed()
        except IndexError:
            self.configStorage.reset_and_save()
            self.on_profile_list_changed()

        self.ui.revalidate_all()
        self.ui.btn_SaveConfig.configure(command=self.save_config)
        self.ui.btn_Generate.configure(command=self.update_and_create)
        self.ui.btn_AddProfile.configure(command=self.create_profile)
        self.ui.btn_DelProfile.configure(command=self.delete_profile)
        self.ui.handle_profile_change = self.change_profile

        self.root.mainloop()


if __name__ == '__main__':
    Application().run()
