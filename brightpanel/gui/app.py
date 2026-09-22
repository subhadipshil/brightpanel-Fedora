"""Main entrypoint for BrightPanel Libadwaita Application."""

from __future__ import annotations
import sys
import os

from brightpanel import __version__, __app_id__
from brightpanel.gui.window import BrightPanelWindow


def run_app(mock_mode: bool = False) -> int:
    """Launches the GTK4 / Libadwaita application."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk, Adw, Gio
    except (ImportError, ValueError) as e:
        print(f"\033[31mError loading GTK4 / Libadwaita: {e}\033[0m", file=sys.stderr)
        print("To install on Fedora Linux, run:\n  sudo dnf install -y python3-gobject libadwaita gtk4", file=sys.stderr)
        return 1

    class BrightPanelApplication(Adw.Application):
        def __init__(self):
            super().__init__(
                application_id=__app_id__,
                flags=Gio.ApplicationFlags.DEFAULT_FLAGS
            )
            self.win = None

        def do_activate(self):
            if not self.win:
                self.win = BrightPanelWindow(self, mock_mode=mock_mode)
            self.win.show()

    app = BrightPanelApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    mock = "--mock" in sys.argv or os.environ.get("MOCK_DDC") == "1"
    sys.exit(run_app(mock_mode=mock))
