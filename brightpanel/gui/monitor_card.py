"""Per-display monitor card widget for Libadwaita."""

from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional, Dict, Any

if TYPE_CHECKING:
    from brightpanel.core.detector import DisplayInfo
    from brightpanel.core.i2c_queue import I2CCommandQueue

from brightpanel.core.vcp_manager import (
    VCPCode,
    INPUT_SOURCES,
    get_input_name
)


def create_monitor_card(
    display: DisplayInfo,
    queue: I2CCommandQueue,
    on_update_cb: Optional[Callable[[str, int], None]] = None
) -> Any:
    """Constructs an Adw.PreferencesGroup / Gtk.Box card for an individual display."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw

    group = Adw.PreferencesGroup()
    group.set_title(display.display_name)
    bus_str = f"/dev/i2c-{display.bus_num}" if display.bus_num >= 0 else "Internal"
    group.set_description(f"Port: {display.connector}  •  Bus: {bus_str}  •  S/N: {display.serial[:16]}")

    # --- Brightness Row ---
    bright_row = Adw.ActionRow()
    bright_row.set_title("Brightness")
    bright_row.set_subtitle(f"{display.current_brightness}%")
    bright_row.set_icon_name("display-brightness-symbolic")

    bright_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    bright_scale.set_value(display.current_brightness)
    bright_scale.set_hexpand(True)
    bright_scale.set_size_request(200, -1)
    bright_scale.set_draw_value(False)

    def on_brightness_changed(scale):
        val = int(scale.get_value())
        bright_row.set_subtitle(f"{val}%")
        queue.set_brightness(display, val)
        if on_update_cb:
            on_update_cb("brightness", val)

    bright_scale.connect("value-changed", on_brightness_changed)

    # Step buttons (-10% / +10%)
    btn_minus = Gtk.Button.new_from_icon_name("list-remove-symbolic")
    btn_minus.set_tooltip_text("Decrease 10%")
    btn_minus.add_css_class("flat")

    def on_minus_clicked(_):
        curr = int(bright_scale.get_value())
        bright_scale.set_value(max(0, curr - 10))

    btn_minus.connect("clicked", on_minus_clicked)

    btn_plus = Gtk.Button.new_from_icon_name("list-add-symbolic")
    btn_plus.set_tooltip_text("Increase 10%")
    btn_plus.add_css_class("flat")

    def on_plus_clicked(_):
        curr = int(bright_scale.get_value())
        bright_scale.set_value(min(100, curr + 10))

    btn_plus.connect("clicked", on_plus_clicked)

    bright_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    bright_box.append(btn_minus)
    bright_box.append(bright_scale)
    bright_box.append(btn_plus)

    bright_row.add_suffix(bright_box)
    group.add(bright_row)

    # --- Contrast Row ---
    if display.is_ddc_supported:
        contrast_row = Adw.ActionRow()
        contrast_row.set_title("Contrast")
        contrast_row.set_subtitle(f"{display.current_contrast}%")
        contrast_row.set_icon_name("weather-clear-night-symbolic")

        contrast_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        contrast_scale.set_value(display.current_contrast)
        contrast_scale.set_hexpand(True)
        contrast_scale.set_size_request(200, -1)
        contrast_scale.set_draw_value(False)

        def on_contrast_changed(scale):
            val = int(scale.get_value())
            contrast_row.set_subtitle(f"{val}%")
            queue.set_contrast(display, val)
            if on_update_cb:
                on_update_cb("contrast", val)

        contrast_scale.connect("value-changed", on_contrast_changed)
        contrast_row.add_suffix(contrast_scale)
        group.add(contrast_row)

    # --- Volume Row (if speaker supported) ---
    if display.is_ddc_supported:
        vol_row = Adw.ActionRow()
        vol_row.set_title("Monitor Speaker Volume")
        vol_row.set_subtitle(f"{display.current_volume}%")
        vol_row.set_icon_name("audio-volume-high-symbolic")

        vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        vol_scale.set_value(display.current_volume)
        vol_scale.set_hexpand(True)
        vol_scale.set_size_request(200, -1)
        vol_scale.set_draw_value(False)

        def on_volume_changed(scale):
            val = int(scale.get_value())
            vol_row.set_subtitle(f"{val}%")
            queue.set_volume(display, val)

        vol_scale.connect("value-changed", on_volume_changed)
        vol_row.add_suffix(vol_scale)
        group.add(vol_row)

    # --- Video Input Source Row ---
    if display.is_ddc_supported:
        input_row = Adw.ComboRow()
        input_row.set_title("Video Input Source")
        input_row.set_icon_name("video-joined-displays-symbolic")

        sources_list = [
            (0x11, "HDMI 1"),
            (0x12, "HDMI 2"),
            (0x0F, "DisplayPort 1"),
            (0x10, "DisplayPort 2"),
            (0x1B, "USB-C / DisplayPort"),
        ]
        string_list = Gtk.StringList()
        selected_idx = 0
        for idx, (code, name) in enumerate(sources_list):
            string_list.append(name)
            if code == display.current_input:
                selected_idx = idx

        input_row.set_model(string_list)
        input_row.set_selected(selected_idx)

        def on_input_selected(row, _):
            idx = row.get_selected()
            if 0 <= idx < len(sources_list):
                code, name = sources_list[idx]
                queue.set_input_source(display, code)

        input_row.connect("notify::selected", on_input_selected)
        group.add(input_row)

    return group
