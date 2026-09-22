"""D-Bus session service implementing org.brightpanel.Daemon."""

from __future__ import annotations
import os
import json
import logging
from typing import List, Dict, Any, Optional

from brightpanel.core.detector import DisplayDetector, DisplayInfo
from brightpanel.core.i2c_queue import I2CCommandQueue
from brightpanel.core.vcp_manager import VCPCode, normalize_input_code
from brightpanel.core.config import ConfigManager
from brightpanel.core.doctor import SystemDoctor

logger = logging.getLogger("brightpanel.daemon")

DBUS_INTROSPECTION_XML = """
<node>
  <interface name="org.brightpanel.Daemon">
    <method name="GetMonitors">
      <arg type="s" name="json_result" direction="out"/>
    </method>
    <method name="SetBrightness">
      <arg type="i" name="display_num" direction="in"/>
      <arg type="i" name="value" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="GetBrightness">
      <arg type="i" name="display_num" direction="in"/>
      <arg type="i" name="value" direction="out"/>
    </method>
    <method name="SetContrast">
      <arg type="i" name="display_num" direction="in"/>
      <arg type="i" name="value" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="SetVolume">
      <arg type="i" name="display_num" direction="in"/>
      <arg type="i" name="value" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="SetInputSource">
      <arg type="i" name="display_num" direction="in"/>
      <arg type="i" name="source_code" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="SetAllBrightness">
      <arg type="i" name="value" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="ApplyPreset">
      <arg type="s" name="preset_name" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="GetDoctorReport">
      <arg type="s" name="json_report" direction="out"/>
    </method>
    <signal name="BrightnessChanged">
      <arg type="i" name="display_num"/>
      <arg type="i" name="value"/>
    </signal>
    <signal name="MonitorsRefreshed"/>
  </interface>
</node>
"""


class BrightPanelDaemon:
    """Core daemon managing monitor states and serving requests."""

    BUS_NAME = "org.brightpanel.Daemon"
    OBJECT_PATH = "/org/brightpanel/Daemon"

    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode or os.environ.get("MOCK_DDC", "0") in ("1", "true", "yes")
        self.detector = DisplayDetector()
        self.queue = I2CCommandQueue()
        self.config = ConfigManager()
        self.doctor = SystemDoctor()
        self.monitors: List[DisplayInfo] = []
        self._dbus_conn: Any = None
        self._registration_id: int = 0

    def initialize(self) -> None:
        """Initializes detector, queue, and discovers initial monitor configuration."""
        self.queue.start()
        self.refresh_monitors()

    def refresh_monitors(self) -> List[DisplayInfo]:
        """Scans for connected displays."""
        self.monitors = self.detector.detect(force_refresh=True, allow_mock=self.mock_mode)
        # Populate initial values into queue cache
        for m in self.monitors:
            self.queue.set_cached_value(m.display_num, VCPCode.BRIGHTNESS, m.current_brightness)
            self.queue.set_cached_value(m.display_num, VCPCode.CONTRAST, m.current_contrast)
            self.queue.set_cached_value(m.display_num, VCPCode.AUDIO_VOLUME, m.current_volume)
        return self.monitors

    def get_monitors_json(self) -> str:
        """Returns JSON representation of currently known displays."""
        data = []
        for m in self.monitors:
            d = m.to_dict()
            # Overlay latest cached values from queue
            d["current_brightness"] = self.queue.get_cached_value(m.display_num, VCPCode.BRIGHTNESS, m.current_brightness)
            d["current_contrast"] = self.queue.get_cached_value(m.display_num, VCPCode.CONTRAST, m.current_contrast)
            d["current_volume"] = self.queue.get_cached_value(m.display_num, VCPCode.AUDIO_VOLUME, m.current_volume)
            data.append(d)
        return json.dumps(data)

    def get_monitor_by_num(self, display_num: int) -> Optional[DisplayInfo]:
        for m in self.monitors:
            if m.display_num == display_num:
                return m
        return None

    def set_brightness(self, display_num: int, value: int) -> bool:
        """Sets brightness for a given display number (1-based), or all if display_num <= 0."""
        if display_num <= 0:
            return self.set_all_brightness(value)

        disp = self.get_monitor_by_num(display_num)
        if not disp:
            return False

        clamped = max(0, min(100, value))
        self.queue.set_brightness(disp, clamped)
        disp.current_brightness = clamped
        self._emit_brightness_changed(display_num, clamped)
        return True

    def get_brightness(self, display_num: int) -> int:
        disp = self.get_monitor_by_num(display_num)
        fallback = disp.current_brightness if disp else 50
        return self.queue.get_cached_value(display_num, VCPCode.BRIGHTNESS, fallback)

    def set_contrast(self, display_num: int, value: int) -> bool:
        disp = self.get_monitor_by_num(display_num)
        if not disp:
            return False
        clamped = max(0, min(100, value))
        self.queue.set_contrast(disp, clamped)
        disp.current_contrast = clamped
        return True

    def set_volume(self, display_num: int, value: int) -> bool:
        disp = self.get_monitor_by_num(display_num)
        if not disp:
            return False
        clamped = max(0, min(100, value))
        self.queue.set_volume(disp, clamped)
        disp.current_volume = clamped
        return True

    def set_input_source(self, display_num: int, source_code: int) -> bool:
        disp = self.get_monitor_by_num(display_num)
        if not disp:
            return False
        self.queue.set_input_source(disp, source_code)
        disp.current_input = source_code
        return True

    def set_all_brightness(self, value: int) -> bool:
        """Sets brightness across all connected displays simultaneously."""
        clamped = max(0, min(100, value))
        for m in self.monitors:
            self.queue.set_brightness(m, clamped)
            m.current_brightness = clamped
            self._emit_brightness_changed(m.display_num, clamped)
        return True

    def apply_preset(self, preset_name: str) -> bool:
        preset = self.config.get_preset(preset_name)
        if not preset:
            return False
        b = preset.get("brightness", 50)
        c = preset.get("contrast", 50)
        for m in self.monitors:
            self.queue.set_brightness(m, b)
            self.queue.set_contrast(m, c)
            m.current_brightness = b
            m.current_contrast = c
            self._emit_brightness_changed(m.display_num, b)
        return True

    def get_doctor_report_json(self) -> str:
        report = [item.to_dict() for item in self.doctor.run_all_checks()]
        return json.dumps(report)

    def _emit_brightness_changed(self, display_num: int, value: int) -> None:
        """Emits D-Bus signal if connection is active."""
        if not self._dbus_conn:
            return
        try:
            from gi.repository import GLib
            params = GLib.Variant("(ii)", (display_num, value))
            self._dbus_conn.emit_signal(
                None,
                self.OBJECT_PATH,
                self.BUS_NAME,
                "BrightnessChanged",
                params
            )
        except Exception as e:
            logger.debug("Failed emitting D-Bus signal: %s", e)

    def start_dbus_service(self) -> None:
        """Exports the daemon to the session D-Bus bus using PyGObject / Gio."""
        try:
            import gi
            gi.require_version("Gio", "2.0")
            gi.require_version("GLib", "2.0")
            from gi.repository import Gio, GLib

            def on_bus_acquired(conn, name):
                logger.info("D-Bus bus acquired: %s", name)
                self._dbus_conn = conn
                node_info = Gio.DBusNodeInfo.new_for_xml(DBUS_INTROSPECTION_XML)

                def method_call(connection, sender, object_path, interface_name, method_name, parameters, invocation):
                    try:
                        if method_name == "GetMonitors":
                            res = self.get_monitors_json()
                            invocation.return_value(GLib.Variant("(s)", (res,)))
                        elif method_name == "SetBrightness":
                            disp_num, val = parameters.unpack()
                            ok = self.set_brightness(disp_num, val)
                            invocation.return_value(GLib.Variant("(b)", (ok,)))
                        elif method_name == "GetBrightness":
                            disp_num, = parameters.unpack()
                            val = self.get_brightness(disp_num)
                            invocation.return_value(GLib.Variant("(i)", (val,)))
                        elif method_name == "SetContrast":
                            disp_num, val = parameters.unpack()
                            ok = self.set_contrast(disp_num, val)
                            invocation.return_value(GLib.Variant("(b)", (ok,)))
                        elif method_name == "SetVolume":
                            disp_num, val = parameters.unpack()
                            ok = self.set_volume(disp_num, val)
                            invocation.return_value(GLib.Variant("(b)", (ok,)))
                        elif method_name == "SetInputSource":
                            disp_num, src = parameters.unpack()
                            ok = self.set_input_source(disp_num, src)
                            invocation.return_value(GLib.Variant("(b)", (ok,)))
                        elif method_name == "SetAllBrightness":
                            val, = parameters.unpack()
                            ok = self.set_all_brightness(val)
                            invocation.return_value(GLib.Variant("(b)", (ok,)))
                        elif method_name == "ApplyPreset":
                            name, = parameters.unpack()
                            ok = self.apply_preset(name)
                            invocation.return_value(GLib.Variant("(b)", (ok,)))
                        elif method_name == "GetDoctorReport":
                            rep = self.get_doctor_report_json()
                            invocation.return_value(GLib.Variant("(s)", (rep,)))
                    except Exception as ex:
                        logger.error("D-Bus method error: %s", ex)
                        invocation.return_dbus_error("org.brightpanel.Error", str(ex))

                self._registration_id = conn.register_object(
                    self.OBJECT_PATH,
                    node_info.interfaces[0],
                    method_call,
                    None,
                    None
                )

            def on_name_acquired(conn, name):
                logger.info("Successfully acquired D-Bus name: %s", name)

            def on_name_lost(conn, name):
                logger.warning("Lost D-Bus name: %s", name)

            Gio.bus_own_name(
                Gio.BusType.SESSION,
                self.BUS_NAME,
                Gio.BusNameOwnerFlags.NONE,
                on_bus_acquired,
                on_name_acquired,
                on_name_lost
            )

            logger.info("Starting BrightPanel D-Bus main loop...")
            loop = GLib.MainLoop()
            loop.run()

        except ImportError:
            logger.warning("PyGObject / Gio not available in this Python environment; running in console loop.")
            import time
            while True:
                time.sleep(1)
