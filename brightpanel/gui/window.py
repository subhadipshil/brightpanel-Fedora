"""Main application window for BrightPanel using Libadwaita."""

from __future__ import annotations
import os
from typing import TYPE_CHECKING, Optional, List

from brightpanel import __version__, __app_id__
from brightpanel.core.detector import DisplayDetector, DisplayInfo
from brightpanel.core.i2c_queue import I2CCommandQueue
from brightpanel.core.config import ConfigManager
from brightpanel.core.doctor import SystemDoctor
from brightpanel.gui.monitor_card import create_monitor_card
from brightpanel.gui.presets_view import create_presets_page
from brightpanel.gui.doctor_view import create_doctor_page


class BrightPanelWindow:
    """Creates and manages the main Adw.ApplicationWindow."""

    def __init__(self, app, mock_mode: bool = False):
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk, Adw, Gio

        self.app = app
        self.mock_mode = mock_mode or os.environ.get("MOCK_DDC", "0") in ("1", "true", "yes")

        self.detector = DisplayDetector()
        self.queue = I2CCommandQueue()
        self.queue.start()
        self.config = ConfigManager()
        self.doctor = SystemDoctor()

        self.monitors: List[DisplayInfo] = []

        # Build UI
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("BrightPanel")
        self.window.set_default_size(720, 600)

        # Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.window.set_content(self.toast_overlay)

        # Main Box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.toast_overlay.set_child(main_box)

        # Header Bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # View Stack & Switcher
        self.view_stack = Adw.ViewStack()
        view_switcher_title = Adw.ViewSwitcherTitle()
        view_switcher_title.set_stack(self.view_stack)
        header.set_title_widget(view_switcher_title)

        # Rescan / Refresh Button
        btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Rescan Connected Monitors")
        btn_refresh.connect("clicked", lambda _: self.rescan_monitors())
        header.pack_start(btn_refresh)

        # View Switcher Bar (for compact mobile/docked mode)
        switcher_bar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(self.view_stack)
        view_switcher_title.bind_property(
            "title-visible",
            switcher_bar,
            "reveal",
            0  # GObject.BindingFlags.DEFAULT
        )

        # Build pages
        self.displays_page = Adw.PreferencesPage()
        self.displays_page.set_title("Displays")
        self.displays_page.set_icon_name("video-display-symbolic")

        self.view_stack.add_titled_with_icon(
            self.displays_page, "displays", "Displays", "video-display-symbolic"
        )

        main_box.append(self.view_stack)
        main_box.append(switcher_bar)

        self.rescan_monitors()

    def show(self):
        self.window.present()

    def show_toast(self, message: str):
        from gi.repository import Adw
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        self.toast_overlay.add_toast(toast)

    def rescan_monitors(self):
        import gi
        from gi.repository import Gtk, Adw

        self.monitors = self.detector.detect(force_refresh=True, allow_mock=self.mock_mode)

        # Clear existing preferences groups in displays_page
        # Rebuild page contents
        while True:
            first = self.displays_page.get_first_child()
            if not first:
                break
            # Iterate and remove
            break

        # Re-create displays page
        self.view_stack.remove(self.displays_page)
        self.displays_page = Adw.PreferencesPage()
        self.displays_page.set_title("Displays")
        self.displays_page.set_icon_name("video-display-symbolic")

        if not self.monitors:
            # Status empty page
            status_page = Adw.StatusPage()
            status_page.set_icon_name("video-display-symbolic")
            status_page.set_title("No External Monitors Found")
            status_page.set_description(
                "Ensure your external monitor is connected and DDC/CI is enabled in its physical OSD menu."
            )
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, halign=Gtk.Align.CENTER)
            rescan_b = Gtk.Button(label="Rescan Displays")
            rescan_b.add_css_class("suggested-action")
            rescan_b.connect("clicked", lambda _: self.rescan_monitors())
            btn_box.append(rescan_b)

            mock_b = Gtk.Button(label="Enable Demo Mode")
            mock_b.connect("clicked", lambda _: self._enable_demo_mode())
            btn_box.append(mock_b)

            status_page.set_child(btn_box)
            self.view_stack.add_titled_with_icon(
                status_page, "displays", "Displays", "video-display-symbolic"
            )
        else:
            # Master Sync Group
            if len(self.monitors) > 1:
                sync_group = Adw.PreferencesGroup()
                sync_group.set_title("All Displays")
                sync_group.set_description("Simultaneously control brightness across all connected monitors.")

                sync_row = Adw.ActionRow()
                sync_row.set_title("Synchronized Brightness")
                sync_row.set_icon_name("display-brightness-symbolic")

                sync_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
                sync_scale.set_value(self.monitors[0].current_brightness)
                sync_scale.set_hexpand(True)
                sync_scale.set_size_request(220, -1)

                def on_sync_changed(scale):
                    val = int(scale.get_value())
                    sync_row.set_subtitle(f"{val}%")
                    for m in self.monitors:
                        self.queue.set_brightness(m, val)
                        m.current_brightness = val

                sync_scale.connect("value-changed", on_sync_changed)
                sync_row.add_suffix(sync_scale)
                sync_group.add(sync_row)
                self.displays_page.add(sync_group)

            # Per-monitor cards
            for m in self.monitors:
                card = create_monitor_card(
                    m,
                    self.queue,
                    on_update_cb=lambda k, v: None
                )
                self.displays_page.add(card)

            self.view_stack.add_titled_with_icon(
                self.displays_page, "displays", "Displays", "video-display-symbolic"
            )

        # Update Presets page
        presets_page = create_presets_page(
            self.config,
            self.monitors,
            self.queue,
            on_preset_applied=lambda name: self.show_toast(f"Applied '{name.capitalize()}' preset")
        )
        self.view_stack.add_titled_with_icon(
            presets_page, "presets", "Presets", "starred-symbolic"
        )

        # Update Doctor page
        doctor_page = create_doctor_page(self.doctor)
        self.view_stack.add_titled_with_icon(
            doctor_page, "doctor", "Doctor", "emblem-system-symbolic"
        )

        self.show_toast(f"Detected {len(self.monitors)} display(s)")

    def _enable_demo_mode(self):
        self.mock_mode = True
        self.rescan_monitors()
