/**
 * BrightPanel - GNOME Shell 45+ Extension
 * Seamless external monitor brightness and contrast control for Fedora Linux.
 */

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Slider from 'resource:///org/gnome/shell/ui/slider.js';
import {Extension, gettext as _} from 'resource:///org/gnome/shell/extensions/extension.js';

const DBUS_NAME = 'org.brightpanel.Daemon';
const DBUS_PATH = '/org/brightpanel/Daemon';
const DBUS_IFACE = 'org.brightpanel.Daemon';

const BrightPanelIndicator = GObject.registerClass(
class BrightPanelIndicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, _('BrightPanel External Monitor Control'));

        this.add_style_class_name('brightpanel-indicator');

        // Top bar icon
        this._icon = new St.Icon({
            icon_name: 'display-brightness-symbolic',
            style_class: 'system-status-icon',
        });
        this.add_child(this._icon);

        this._monitors = [];
        this._proxy = null;
        this._initDBus();

        // Refresh monitors when user clicks panel icon
        this.menu.connect('open-state-changed', (menu, isOpen) => {
            if (isOpen) {
                this._fetchMonitors();
            }
        });

        this._buildMenu();
    }

    _initDBus() {
        try {
            Gio.DBusProxy.new_for_bus(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.NONE,
                null,
                DBUS_NAME,
                DBUS_PATH,
                DBUS_IFACE,
                null,
                (initable, result) => {
                    try {
                        this._proxy = Gio.DBusProxy.new_for_bus_finish(result);
                        this._fetchMonitors();
                    } catch (e) {
                        // Daemon may not be running yet; CLI fallback used
                    }
                }
            );
        } catch (err) {
            console.error('[BrightPanel] DBus init error:', err);
        }
    }

    _fetchMonitors() {
        if (this._proxy) {
            this._proxy.call(
                'GetMonitors',
                null,
                Gio.DBusCallFlags.NONE,
                -1,
                null,
                (proxy, res) => {
                    try {
                        const reply = proxy.call_finish(res);
                        const [jsonStr] = reply.recursiveUnpack();
                        this._monitors = JSON.parse(jsonStr);
                        this._rebuildMenuItems();
                    } catch (e) {
                        this._fetchViaCLI();
                    }
                }
            );
        } else {
            this._fetchViaCLI();
        }
    }

    _fetchViaCLI() {
        try {
            const [ok, stdout] = GLib.spawn_command_line_sync('brightpanel list --json');
            if (ok && stdout) {
                const text = new TextDecoder().decode(stdout);
                this._monitors = JSON.parse(text);
                this._rebuildMenuItems();
            }
        } catch (e) {
            // No monitors or CLI not yet on PATH
        }
    }

    _buildMenu() {
        this.menu.removeAll();

        // Header
        const headerItem = new PopupMenu.PopupMenuItem(_('BrightPanel Monitors'), {reactive: false});
        headerItem.label.add_style_class_name('brightpanel-slider-title');
        this.menu.addMenuItem(headerItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        if (this._monitors.length === 0) {
            const emptyItem = new PopupMenu.PopupMenuItem(_('No external monitors detected'));
            emptyItem.connect('activate', () => this._fetchMonitors());
            this.menu.addMenuItem(emptyItem);
        } else {
            this._monitors.forEach(mon => {
                this._addMonitorSliders(mon);
            });
        }

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Quick Presets Row
        const presetsItem = new PopupMenu.PopupSubMenuMenuItem(_('Lighting Presets'));
        const presets = [
            {name: 'Daylight (100%)', preset: 'daylight'},
            {name: 'Office (75%)', preset: 'office'},
            {name: 'Coding (55%)', preset: 'coding'},
            {name: 'Reading (35%)', preset: 'reading'},
            {name: 'Night (15%)', preset: 'night'},
        ];

        presets.forEach(p => {
            const sub = new PopupMenu.PopupMenuItem(p.name);
            sub.connect('activate', () => {
                this._applyPreset(p.preset);
            });
            presetsItem.menu.addMenuItem(sub);
        });
        this.menu.addMenuItem(presetsItem);

        // Control Panel Launcher
        const appItem = new PopupMenu.PopupMenuItem(_('Open BrightPanel App'));
        appItem.connect('activate', () => {
            try {
                Gio.Subprocess.new(['brightpanel-gui'], Gio.SubprocessFlags.NONE);
            } catch (err) {
                GLib.spawn_command_line_async('brightpanel list');
            }
        });
        this.menu.addMenuItem(appItem);
    }

    _rebuildMenuItems() {
        this._buildMenu();
    }

    _addMonitorSliders(mon) {
        // Monitor Title
        const titleItem = new PopupMenu.PopupMenuItem(
            `${mon.display_name} (${mon.connector})`,
            {reactive: false}
        );
        this.menu.addMenuItem(titleItem);

        // Brightness Slider
        const sliderItem = new PopupMenu.PopupBaseMenuItem({activate: false});
        const icon = new St.Icon({
            icon_name: 'display-brightness-symbolic',
            style_class: 'popup-menu-icon',
        });
        sliderItem.add_child(icon);

        const initialVal = (mon.current_brightness || 50) / 100.0;
        const slider = new Slider.Slider(initialVal);
        sliderItem.add_child(slider);

        const label = new St.Label({
            text: `${mon.current_brightness || 50}%`,
            y_align: Clutter.ActorAlign.CENTER,
        });
        sliderItem.add_child(label);

        slider.connect('notify::value', () => {
            const pct = Math.round(slider.value * 100);
            label.set_text(`${pct}%`);
        });

        slider.connect('drag-end', () => {
            const pct = Math.round(slider.value * 100);
            this._setBrightness(mon.display_num, pct);
        });

        this.menu.addMenuItem(sliderItem);
    }

    _setBrightness(displayNum, value) {
        if (this._proxy) {
            this._proxy.call(
                'SetBrightness',
                new GLib.Variant('(ii)', [displayNum, value]),
                Gio.DBusCallFlags.NONE,
                -1,
                null,
                null
            );
        } else {
            GLib.spawn_command_line_async(`brightpanel set ${value} -m ${displayNum} -q`);
        }
    }

    _applyPreset(presetName) {
        if (this._proxy) {
            this._proxy.call(
                'ApplyPreset',
                new GLib.Variant('(s)', [presetName]),
                Gio.DBusCallFlags.NONE,
                -1,
                null,
                () => this._fetchMonitors()
            );
        } else {
            GLib.spawn_command_line_async(`brightpanel preset ${presetName} -q`);
        }
    }
});

export default class BrightPanelExtension extends Extension {
    enable() {
        this._indicator = new BrightPanelIndicator();
        Main.panel.addToStatusArea('brightpanel-indicator', this._indicator);
    }

    disable() {
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}
