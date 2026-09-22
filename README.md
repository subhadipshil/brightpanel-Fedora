# BrightPanel (Fedora Linux)

<p align="center">
  <img src="packaging/icons/io.github.subhadipshil.brightpanel.svg" width="132" height="132" alt="BrightPanel Logo"/>
</p>

<h2 align="center">Production-Grade External Monitor Control Suite for Fedora Linux</h2>

<p align="center">
  Seamless hardware DDC/CI brightness, contrast, audio volume, and input switching for external displays connected via HDMI, DisplayPort, and USB-C.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Fedora-38%20|%2039%20|%2040%20|%2041%20|%20Rawhide-294172?logo=fedora&logoColor=white" alt="Fedora Support"/>
  <img src="https://img.shields.io/badge/GNOME-45%20|%2046%20|%2047%20|%2048-4a86cf?logo=gnome&logoColor=white" alt="GNOME Shell Support"/>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white" alt="Python 3"/>
  <img src="https://img.shields.io/badge/UI-Libadwaita%20%2F%20GTK4-3584e4" alt="Libadwaita GTK4"/>
  <img src="https://img.shields.io/badge/Tests-24%20Passed-success" alt="Tests Passed"/>
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"/>
</p>

<p align="center">
  <a href="#the-problem">The Problem</a> •
  <a href="#key-features">Key Features</a> •
  <a href="#visual-overview">Visual Overview</a> •
  <a href="#quick-installation-fedora">Installation</a> •
  <a href="#gnome-shell-extension">GNOME Extension</a> •
  <a href="#cli--keyboard-shortcuts">CLI & Shortcuts</a> •
  <a href="#system-doctor--troubleshooting">Doctor & Diagnostics</a> •
  <a href="#dbus-api-specification">D-Bus API</a> •
  <a href="#architecture">Architecture</a>
</p>

---

### ⚡ 1-Line Quick Install (Auto-Clones & Installs)
Open your Fedora terminal and paste:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/subhadipshil/brightpanel-Fedora/main/install.sh)"
```

*Or with standard git clone:*

```bash
git clone https://github.com/subhadipshil/brightpanel-Fedora.git && cd "brightpanel Fedora" && chmod +x install.sh && ./install.sh
```

---

## The Problem
On Linux desktop environments (including Fedora Workstation), the native brightness slider only controls the internal laptop screen backlight via `/sys/class/backlight`. External monitors connected over HDMI, DisplayPort, or USB-C/Thunderbolt rely on **DDC/CI** (Display Data Channel Command Interface) over I2C buses (`/dev/i2c-*`).

Without BrightPanel, external monitor control on Linux suffers from:
- ❌ **I2C Bus Contention & Freezes**: Directly invoking command-line tools like `ddcutil` during slider dragging floods the monitor's low-speed I2C bus, causing frame drops, timeouts, and monitor crashes.
- ❌ **Root Permission Friction**: `/dev/i2c-*` devices are restricted to `root` by default on Fedora unless udev rules and `i2c-dev` kernel modules are configured.
- ❌ **Fragmented Experience**: No cohesive bridge between the GNOME Top Panel, Quick Settings, desktop GUI, and custom keyboard hotkeys.

**BrightPanel** solves this with an integrated, production-grade ecosystem.

---

## Feature Comparison

| Feature | Standard Fedora / GNOME | Ad-hoc Scripts / ddcutil CLI | BrightPanel Suite |
| :--- | :---: | :---: | :---: |
| **External Monitor Brightness** | ❌ (Internal only) | ⚠️ (Slow, blocking) | ✅ **Instant & Smooth** |
| **I2C Debouncing & Queuing** | ❌ | ❌ (Causes I2C lockup) | ✅ **Zero-Flicker Queue** |
| **Top Panel Sliders** | ❌ | ❌ | ✅ **GNOME 45+ ESM Extension** |
| **Libadwaita Control Panel** | ❌ | ❌ | ✅ **Native GNOME App** |
| **Multi-Monitor Master Sync** | ❌ | ❌ | ✅ **Unified Master Slider** |
| **Audio Volume & Contrast** | ❌ | ⚠️ (Manual hex commands) | ✅ **Visual Sliders** |
| **Video Input Source Switcher** | ❌ | ⚠️ (Manual VCP hex) | ✅ **1-Click KVM Switch** |
| **Automated System Doctor** | ❌ | ❌ | ✅ **1-Click Fedora Audit** |
| **Fedora RPM / udev Setup** | ❌ | ❌ (Manual setup) | ✅ **Automated `install.sh`** |

---

## Visual Overview

### 1. GNOME Shell Top Panel Extension
```
  [Activities]           12:45 PM           [ 󰃠 ] [ 󰕾 ] [ 󰤨 ] [  v  ]
                                              │
  ┌───────────────────────────────────────────┴────────────────────────┐
  │  BrightPanel External Monitors                                     │
  │  ───────────────────────────────────────────────────────────────── │
  │  Dell UltraSharp U2723QE (card0-DP-1)                              │
  │  󰃠  [═══════════════════════════════════════●──────]  80%          │
  │                                                                    │
  │  LG UltraFine 4K (card0-HDMI-A-1)                                  │
  │  󰃠  [══════════════════════●───────────────────────]  50%          │
  │  ───────────────────────────────────────────────────────────────── │
  │  Lighting Presets                                                > │
  │    • Daylight (100%)    • Coding (55%)      • Night Shift (15%)    │
  │    • Office (75%)       • Reading (35%)     • Minimal (5%)         │
  │  ───────────────────────────────────────────────────────────────── │
  │    Open BrightPanel App...                                        │
  └────────────────────────────────────────────────────────────────────┘
```

### 2. Native Libadwaita Desktop Control Center
```
  ┌─ BrightPanel ─────────────────────────────────────────────── [─] [□] [✕] ─┐
  │  [ 󰑐 Rescan ]           ( Displays )  ( Presets )  ( Doctor )             │
  │                                                                           │
  │  ALL DISPLAYS                                                             │
  │  ┌─────────────────────────────────────────────────────────────────────┐  │
  │  │  󰃠  Synchronized Brightness        [══════════════════●─────]  75%  │  │
  │  └─────────────────────────────────────────────────────────────────────┘  │
  │                                                                           │
  │  Dell UltraSharp U2723QE                                                  │
  │  Port: DP-1  •  Bus: /dev/i2c-4  •  S/N: CN-0P826F-74445                   │
  │  ┌─────────────────────────────────────────────────────────────────────┐  │
  │  │  󰃠  Brightness         [-]  [══════════════════════●──]  80%  [+]    │  │
  │  │  󰖔  Contrast                 [══════════════════●─────]  70%        │  │
  │  │  󰕾  Monitor Speaker Volume   [══════════●─────────────]  40%        │  │
  │  │  󰍹  Video Input Source       [ DisplayPort 1                      v ]│  │
  │  └─────────────────────────────────────────────────────────────────────┘  │
  │                                                                           │
  │  LG UltraFine 4K                                                          │
  │  Port: HDMI-A-1  •  Bus: /dev/i2c-5  •  S/N: 108NTXF9K219                 │
  │  ┌─────────────────────────────────────────────────────────────────────┐  │
  │  │  󰃠  Brightness         [-]  [══════════════●──────────]  55%  [+]    │  │
  │  │  󰖔  Contrast                 [══════════════●──────────]  50%        │  │
  │  │  󰍹  Video Input Source       [ HDMI 1                             v ]│  │
  │  └─────────────────────────────────────────────────────────────────────┘  │
  └───────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Installation (Fedora)

BrightPanel supports Fedora 38, 39, 40, 41, 42, and Rawhide.

### Method 1: Instant One-Line Remote Installer (Fastest)
Automatically clones into a temporary directory and executes the full Fedora setup:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/subhadipshil/brightpanel-Fedora/main/install.sh)"
```

### Method 2: Git Clone & Install
If you prefer to clone the repository to your machine first:

```bash
git clone https://github.com/subhadipshil/brightpanel-Fedora.git
cd "brightpanel Fedora"
chmod +x install.sh
./install.sh
```

**What the installer does automatically:**
1. Installs dependencies via DNF (`ddcutil`, `python3-gobject`, `libadwaita`, `gtk4`, `i2c-tools`).
2. Configures `/etc/modules-load.d/i2c-dev.conf` so the `i2c-dev` kernel module loads at boot.
3. Installs udev rule `/etc/udev/rules.d/45-ddcutil-i2c.rules` with `TAG+="uaccess"` and group `i2c`.
4. Adds your user to the `i2c` group for rootless DDC/CI access.
5. Installs the desktop application, SVG icon, and CLI symlinks (`/usr/local/bin/brightpanel`).
6. Installs and enables the GNOME Shell 45+ extension (`brightpanel@subhadipshil.github.com`).
7. Configures and starts the background session daemon (`systemctl --user enable --now brightpanel.service`).

> [!IMPORTANT]
> Because your user account is added to the `i2c` group, **log out and log back into your desktop session** (or reboot) after installation so Linux activates your new group permissions.

### Method 2: Fedora RPM Build
For standard RPM package management or local repository deployment:

```bash
sudo dnf install -y rpm-build python3-devel systemd-rpm-macros
rpmbuild -ba packaging/brightpanel.spec
sudo dnf install -y ~/rpmbuild/RPMS/noarch/brightpanel-1.0.0-1.fc*.noarch.rpm
```

### Method 3: Fedora Silverblue / Kinoite / Bazzite (rpm-ostree)
For immutable Fedora systems:

```bash
# Overlay required runtime packages
rpm-ostree install ddcutil i2c-tools
systemctl reboot

# Then install BrightPanel locally
./install.sh
```

---

## GNOME Shell Extension

The included GNOME Shell extension integrates directly with GNOME 45, 46, 47, and 48:
- **Instant Access**: Click the brightness icon in the Top Bar to view sliders and change settings without opening any window.
- **D-Bus Connected**: Sliders talk directly to `org.brightpanel.Daemon` over session D-Bus for lag-free performance.
- **Extension Toggle**: Manage it anytime in Fedora's **Extensions** or **Extension Manager** app (`brightpanel@subhadipshil.github.com`).

---

## CLI & Custom Keyboard Shortcuts

BrightPanel features a high-performance CLI designed for scripting and keyboard hotkeys.

### Command Reference

```bash
# List all detected external displays
brightpanel list
brightpanel list --json

# Set brightness (0-100%) across all monitors
brightpanel set 80

# Set brightness on a specific display (#1 or #2)
brightpanel set 50 -m 1

# Increment / Decrement brightness (ideal for hotkeys!)
brightpanel inc 10
brightpanel dec 10
brightpanel inc 5 -m 2

# Adjust contrast (0-100%)
brightpanel contrast 70

# Adjust monitor speaker volume
brightpanel volume 40

# Switch monitor video input source (KVM switching)
brightpanel input dp1       # DisplayPort 1
brightpanel input hdmi1     # HDMI 1
brightpanel input hdmi2     # HDMI 2
brightpanel input usbc      # USB-C / DP-Alt mode

# Apply lighting presets
brightpanel preset daylight   # 100% bright, 75% contrast
brightpanel preset office     # 75% bright, 70% contrast
brightpanel preset coding     # 55% bright, 65% contrast
brightpanel preset reading    # 35% bright, 50% contrast
brightpanel preset night      # 15% bright, 45% contrast
brightpanel preset minimal    # 5% bright, 35% contrast

# Run system diagnostic audit
brightpanel doctor
brightpanel doctor --json

# One-command permissions setup
brightpanel setup
```

### Configuring Fedora Keyboard Shortcuts

To bind external monitor brightness to keyboard shortcuts in Fedora GNOME:
1. Open **Settings** -> **Keyboard** -> **View and Customize Shortcuts** -> **Custom Shortcuts**.
2. Click **+** (Add Shortcut):
   - **Name**: `Monitor Brightness Up`
   - **Command**: `brightpanel inc 10 -q`
   - **Shortcut**: `Super + F6` (or `F6`)
3. Click **+** (Add Shortcut):
   - **Name**: `Monitor Brightness Down`
   - **Command**: `brightpanel dec 10 -q`
   - **Shortcut**: `Super + F5` (or `F5`)

---

## System Doctor & Troubleshooting

If your external monitor is not detected or does not respond, run:

```bash
brightpanel doctor
```

Sample output:
```
=====================================================
       BrightPanel System Doctor - Fedora Audit       
=====================================================

[PASS] ddcutil Binary
       Found: /usr/bin/ddcutil (ddcutil 2.1.4)
[PASS] Kernel Module (i2c-dev)
       i2c-dev module is loaded and configured to load at boot.
[PASS] udev Permissions Rules
       Found udev rule: /etc/udev/rules.d/45-ddcutil-i2c.rules
[PASS] User Group (i2c)
       User 'subha' is a member of the 'i2c' group.
[PASS] I2C Device Nodes (/dev/i2c-*)
       6 of 6 I2C device nodes are read/write accessible.
[PASS] Connected Displays (DDC/CI)
       Detected 2 display(s) communicating via DDC/CI.

All core system checks passed! External monitor controls ready.
```

### Common Hardware Gotchas
1. **Monitor OSD Setting**: Open your monitor's physical button menu (OSD) and ensure **DDC/CI** is set to **Enabled**. (On some Dell, LG, ASUS, Samsung, and BenQ screens, this is under *System Settings* or *Others*).
2. **DisplayPort / HDMI Cables**: Some cheap HDMI adapters or USB hubs block I2C lines. Direct DisplayPort, HDMI, or Thunderbolt/USB-C cables pass DDC/CI signals reliably.
3. **Group Permissions**: If `doctor` reports you are not in the `i2c` group, run `brightpanel setup` and log out/in.

---

## D-Bus API Specification

BrightPanel exposes a session D-Bus interface for scripting, extensions, and integration:

- **Bus Name**: `org.brightpanel.Daemon`
- **Object Path**: `/org/brightpanel/Daemon`
- **Interface**: `org.brightpanel.Daemon`

### Methods

| Method | Parameters | Return | Description |
| :--- | :--- | :--- | :--- |
| `GetMonitors()` | None | `s (json_str)` | Returns list of detected monitors with current states. |
| `SetBrightness(i, i)` | `display_num`, `value` | `b (success)` | Sets brightness (0-100) on specified monitor. |
| `GetBrightness(i)` | `display_num` | `i (value)` | Gets cached brightness for monitor. |
| `SetContrast(i, i)` | `display_num`, `value` | `b (success)` | Sets contrast (0-100). |
| `SetVolume(i, i)` | `display_num`, `value` | `b (success)` | Sets monitor speaker volume (0-100). |
| `SetInputSource(i, i)`| `display_num`, `code` | `b (success)` | Switches video input source. |
| `SetAllBrightness(i)` | `value` | `b (success)` | Synchronously sets brightness across all displays. |
| `ApplyPreset(s)` | `preset_name` | `b (success)` | Applies lighting preset by name. |
| `GetDoctorReport()` | None | `s (json_report)` | Returns full system diagnostics audit JSON. |

### Signals

| Signal | Parameters | Description |
| :--- | :--- | :--- |
| `BrightnessChanged` | `i (display_num)`, `i (value)` | Emitted whenever any display brightness changes. |
| `MonitorsRefreshed` | None | Emitted when display topology changes. |

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                   User Interfaces                      │
│   GNOME Extension  │  Libadwaita GUI  │  CLI / Hotkeys │
└──────────────┬──────────────────┬───────────────┬──────┘
               │                  │               │
               ▼                  ▼               ▼
┌────────────────────────────────────────────────────────┐
│            org.brightpanel.Daemon (D-Bus)              │
│       • High-speed in-memory state cache               │
│       • Multi-display topology discovery               │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│              I2C Command Queue & Worker                │
│       • Per-bus serialization (prevents lockup)        │
│       • 100ms Debouncer (smooth slider dragging)       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│         Hardware DDC/CI Communication (ddcutil)        │
│      /dev/i2c-* (VESA MCCS: 0x10, 0x12, 0x60, 0x62)    │
└────────────────────────────────────────────────────────┘
```

---

## Testing & Development

BrightPanel includes an automated unit test suite:

```bash
# Run all 24 unit tests
python -m unittest discover -s tests -v
```

### Simulated Mode (Mock Engine)
To test and develop BrightPanel on any machine without physical DDC/CI monitors attached (e.g. VMs, WSL, laptops):

```bash
# CLI in simulation mode
brightpanel list --mock
brightpanel set 85 --mock
brightpanel preset reading --mock

# Desktop GUI in simulation mode
brightpanel-gui --mock
```

---

## Uninstallation

To cleanly remove BrightPanel:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

---

## License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.
