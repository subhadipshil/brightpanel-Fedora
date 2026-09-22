"""Interactive system diagnostics view for Libadwaita."""

from __future__ import annotations
import subprocess
from typing import Any

from brightpanel.core.doctor import SystemDoctor


def create_doctor_page(doctor: SystemDoctor) -> Any:
    """Creates an Adw.PreferencesPage showing Fedora DDC/CI system diagnostics."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw

    page = Adw.PreferencesPage()
    page.set_title("Doctor")
    page.set_icon_name("emblem-system-symbolic")

    group = Adw.PreferencesGroup()
    group.set_title("Fedora System & Hardware Diagnostics")
    group.set_description("Audits kernel modules, user permissions, and DDC/CI bus connectivity.")

    checks = doctor.run_all_checks()
    for item in checks:
        row = Adw.ActionRow()
        row.set_title(item.name)
        row.set_subtitle(item.message)

        if item.status == "OK":
            row.set_icon_name("emblem-ok-symbolic")
        elif item.status == "WARN":
            row.set_icon_name("dialog-warning-symbolic")
        else:
            row.set_icon_name("dialog-error-symbolic")

        if item.fix_command:
            btn = Gtk.Button(label="Copy Fix")
            btn.set_tooltip_text(item.fix_command)

            def make_copy(cmd=item.fix_command):
                def handler(button):
                    clipboard = button.get_display().get_clipboard()
                    clipboard.set(cmd)
                    button.set_label("Copied!")
                return handler

            btn.connect("clicked", make_copy())
            row.add_suffix(btn)

        group.add(row)

    # Actions group
    actions_group = Adw.PreferencesGroup()
    actions_row = Adw.ActionRow()
    actions_row.set_title("Automated Permissions Setup")
    actions_row.set_subtitle("Run 'brightpanel setup' in terminal to configure i2c-dev and udev rules.")

    btn_setup = Gtk.Button(label="Run Setup Script")
    btn_setup.add_css_class("suggested-action")

    def on_setup_clicked(_):
        try:
            subprocess.Popen(["brightpanel", "setup"])
        except Exception:
            pass

    btn_setup.connect("clicked", on_setup_clicked)
    actions_row.add_suffix(btn_setup)
    actions_group.add(actions_row)

    page.add(group)
    page.add(actions_group)
    return page
