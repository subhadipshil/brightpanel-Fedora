"""Presets selection and management view for Libadwaita."""

from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Any

if TYPE_CHECKING:
    from brightpanel.core.config import ConfigManager
    from brightpanel.core.i2c_queue import I2CCommandQueue
    from brightpanel.core.detector import DisplayInfo


def create_presets_page(
    config: ConfigManager,
    monitors: list[DisplayInfo],
    queue: I2CCommandQueue,
    on_preset_applied: Callable[[str], None]
) -> Any:
    """Creates an Adw.PreferencesPage for presets."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw

    page = Adw.PreferencesPage()
    page.set_title("Presets")
    page.set_icon_name("starred-symbolic")

    group = Adw.PreferencesGroup()
    group.set_title("Lighting Presets")
    group.set_description("Instantly adjust all external monitors to matched lighting environments.")

    for name, vals in config.data.presets.items():
        row = Adw.ActionRow()
        row.set_title(name.capitalize())
        b = vals.get("brightness", 50)
        c = vals.get("contrast", 50)
        row.set_subtitle(f"Brightness: {b}%  •  Contrast: {c}%")

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")

        def make_handler(p_name=name, p_b=b, p_c=c):
            def handler(_):
                for m in monitors:
                    queue.set_brightness(m, p_b)
                    queue.set_contrast(m, p_c)
                    m.current_brightness = p_b
                    m.current_contrast = p_c
                on_preset_applied(p_name)
            return handler

        apply_btn.connect("clicked", make_handler())
        row.add_suffix(apply_btn)
        group.add(row)

    page.add(group)
    return page
