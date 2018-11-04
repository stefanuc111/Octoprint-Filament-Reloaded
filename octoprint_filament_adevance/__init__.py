# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.events import eventManager, Events
from flask import jsonify, make_response
from octoprint.util import RepeatedTimer
import threading

class FilamentReloadedPlugin(octoprint.plugin.StartupPlugin,
                             octoprint.plugin.EventHandlerPlugin,
                             octoprint.plugin.TemplatePlugin,
                             octoprint.plugin.SettingsPlugin):

    def initialize(self):
        return


    def on_after_startup(self):
        self._logger.info("Filament Sensor Adevance started")
        self.pin = int(self._settings.get(["pin"]))
        self.switch = int(self._settings.get(["switch"]))

        if self.pin != -1:   # If a pin is defined
            self._logger.info("Filament Sensor active on GPIO Pin [%s]"%self.pin)
            try:
                    export = open("/sys/class/gpio/export","w")
                    export.write(str(self.pin))
                    export.close()
                    sleep(0.1)
            except:
	            pass

            t = threading.Timer(1.0, self.init_direction)
            t.start()  # after 30 seconds, "hello, world" will be printed   


    def init_direction(self):
        self._logger.info("Initializing filament sensor direction")
        direction = open("/sys/class/gpio/gpio" + str(self.pin) + "/direction","w")
        direction.write("in")
        direction.close()
   

    def start_timer(self):
        self._logger.info("Printing started: Filament sensor enabled")
        self.stop_timer();
        self.timer = RepeatedTimer(1.0, self.check_gpio)
        self.timer.start();

    def stop_timer(self):
        self._logger.info("Printing stopped: Filament sensor disabled")
        try:
            self.timer.cancel();
        except:
            pass

    def get_pin_state(self):
        gpio_pin = open("/sys/class/gpio/gpio" + str(self.pin) + "/value","r")
        state = gpio_pin.read()
        state = int(state[0]);
        gpio_pin.close()
        return state

    def get_settings_defaults(self):
        return dict(
            pin     = -1,   # Default is no pin
            no_filament_gcode = '',
            pause_print = True,
            switch  = 0    # Normally Open
        )

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=False)]

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:  # If a new print is beginning
            if self.pin != -1:
                self.start_timer();
        elif event in (Events.PRINT_DONE, Events.PRINT_FAILED, Events.PRINT_CANCELLED):
            self.stop_timer();

    def check_gpio(self):
        state = self.get_pin_state()
        self._logger.debug("Detected sensor state [%s]"%(state))
        if state != self.switch:    # If the sensor is tripped
            self._logger.debug("Sensor [%s]"%state)
            if self._printer.is_printing():
                if self.pause_print:
                    self._printer.toggle_pause_print()
                if self.no_filament_gcode:
                    self._logger.info("Sending out of filament GCODE")
                    self._printer.commands(self.no_filament_gcode)

    def get_update_information(self):
        return dict(
            octoprint_filament=dict(
                displayName="Filament Sensor Adevance",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="stefanuc111",
                repo="Octoprint-Filament-Reloaded",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/stefanuc111/Octoprint-Filament-Reloaded/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "Filament Sensor Adevance"
__plugin_version__ = "1.0.13"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = FilamentReloadedPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.scripts": __plugin_implementation__.on_print_paused_hook}
