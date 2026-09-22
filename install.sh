#!/usr/bin/env bash
# ==============================================================================
# BrightPanel - Production-Grade Installer for Fedora Linux
# https://github.com/subhadipshil/brightpanel-Fedora
# ==============================================================================

set -e

COLOR_CYAN='\033[1;36m'
COLOR_GREEN='\033[1;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[1;31m'
COLOR_RESET='\033[0m'

echo -e "${COLOR_CYAN}"
echo "========================================================================"
echo "          BrightPanel - External Monitor Control for Fedora"
echo "========================================================================"
echo -e "${COLOR_RESET}"

# Determine script and source directories (handles pipe/curl execution)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

if [ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/packaging" ]; then
    SRC_DIR="$SCRIPT_DIR"
else
    echo -e "\n${COLOR_CYAN}Auto-cloning BrightPanel repository from GitHub...${COLOR_RESET}"
    SRC_DIR="/tmp/brightpanel-install-$$"
    mkdir -p "$SRC_DIR"
    git clone --depth 1 https://github.com/subhadipshil/brightpanel-Fedora.git "$SRC_DIR"
    trap 'rm -rf "$SRC_DIR"' EXIT
fi

cd "$SRC_DIR"

# Determine actual non-root user
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)

if [ -z "$TARGET_HOME" ]; then
    TARGET_HOME="$HOME"
fi

# Verify Fedora OS
if [ -f /etc/fedora-release ]; then
    FEDORA_VER=$(cat /etc/fedora-release)
    echo -e "Detected OS: ${COLOR_GREEN}${FEDORA_VER}${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}Warning: Non-Fedora distribution detected. Proceeding with Fedora-compatible setup...${COLOR_RESET}"
fi

# Step 1: Install system dependencies via DNF
echo -e "\n${COLOR_CYAN}[1/7] Installing required system packages via DNF...${COLOR_RESET}"
DNF_BIN=$(command -v dnf5 || command -v dnf)

if [ -n "$DNF_BIN" ]; then
    sudo $DNF_BIN install -y \
        ddcutil \
        python3-gobject \
        libadwaita \
        gtk4 \
        i2c-tools \
        python3-pip \
        python3-setuptools
else
    echo -e "${COLOR_RED}Error: Neither dnf nor dnf5 found!${COLOR_RESET}"
    exit 1
fi

# Step 2: Configure i2c-dev kernel module
echo -e "\n${COLOR_CYAN}[2/7] Configuring i2c-dev kernel module...${COLOR_RESET}"
sudo modprobe i2c-dev || true
echo "i2c-dev" | sudo tee /etc/modules-load.d/i2c-dev.conf > /dev/null
echo -e "${COLOR_GREEN}i2c-dev module configured to load at boot.${COLOR_RESET}"

# Step 3: Configure udev rules & user group permissions
echo -e "\n${COLOR_CYAN}[3/7] Setting up udev rules and user group permissions...${COLOR_RESET}"
sudo groupadd -f i2c
sudo usermod -aG i2c "$TARGET_USER"

sudo cp packaging/45-ddcutil-i2c.rules /etc/udev/rules.d/45-ddcutil-i2c.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
echo -e "${COLOR_GREEN}User '${TARGET_USER}' added to group 'i2c' and udev rules installed.${COLOR_RESET}"

# Step 4: Install BrightPanel Python package & CLI
echo -e "\n${COLOR_CYAN}[4/7] Installing BrightPanel application and CLI...${COLOR_RESET}"
sudo pip3 install --no-deps -e . || sudo python3 setup.py install

# Step 5: Install Desktop entry and Application Icons
echo -e "\n${COLOR_CYAN}[5/7] Installing Desktop launcher and icons...${COLOR_RESET}"
sudo install -D -p -m 0644 packaging/io.github.subhadipshil.brightpanel.desktop /usr/share/applications/io.github.subhadipshil.brightpanel.desktop
sudo install -D -p -m 0644 packaging/io.github.subhadipshil.brightpanel.metainfo.xml /usr/share/metainfo/io.github.subhadipshil.brightpanel.metainfo.xml
sudo install -D -p -m 0644 packaging/icons/io.github.subhadipshil.brightpanel.svg /usr/share/icons/hicolor/scalable/apps/io.github.subhadipshil.brightpanel.svg

if command -v update-desktop-database > /dev/null 2>&1; then
    sudo update-desktop-database /usr/share/applications > /dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor > /dev/null 2>&1 || true
fi

# Step 6: Install GNOME Shell Extension
echo -e "\n${COLOR_CYAN}[6/7] Installing GNOME Shell Extension...${COLOR_RESET}"
EXT_DIR="$TARGET_HOME/.local/share/gnome-shell/extensions/brightpanel@subhadipshil.github.com"
mkdir -p "$EXT_DIR"
cp -r extension/* "$EXT_DIR/"
chown -R "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.local/share/gnome-shell"

echo -e "${COLOR_GREEN}GNOME extension installed to $EXT_DIR${COLOR_RESET}"
if command -v gnome-extensions > /dev/null 2>&1; then
    sudo -u "$TARGET_USER" gnome-extensions enable brightpanel@subhadipshil.github.com 2>/dev/null || true
fi

# Step 7: Install and start Systemd user daemon service
echo -e "\n${COLOR_CYAN}[7/7] Setting up BrightPanel systemd user service...${COLOR_RESET}"
SYSTEMD_USER_DIR="$TARGET_HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
cp packaging/brightpanel.service "$SYSTEMD_USER_DIR/brightpanel.service"
chown -R "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.config/systemd"

sudo -u "$TARGET_USER" systemctl --user daemon-reload 2>/dev/null || true
sudo -u "$TARGET_USER" systemctl --user enable --now brightpanel.service 2>/dev/null || true

echo -e "\n${COLOR_GREEN}========================================================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}       BrightPanel successfully installed on Fedora!                    ${COLOR_RESET}"
echo -e "${COLOR_GREEN}========================================================================${COLOR_RESET}"
echo ""
echo -e "Important Note on Permissions:"
echo -e "Because your user account was just added to the '${COLOR_CYAN}i2c${COLOR_RESET}' group,"
echo -e "please ${COLOR_YELLOW}log out and log back into your desktop session${COLOR_RESET} (or reboot)"
echo -e "so Linux activates your new group permissions for external monitor I2C access."
echo ""
echo -e "Quick Usage:"
echo -e "  ${COLOR_CYAN}brightpanel-gui${COLOR_RESET}        Launch the Libadwaita control panel"
echo -e "  ${COLOR_CYAN}brightpanel list${COLOR_RESET}       List connected external monitors"
echo -e "  ${COLOR_CYAN}brightpanel set 80${COLOR_RESET}     Set brightness to 80%"
echo -e "  ${COLOR_CYAN}brightpanel inc 10${COLOR_RESET}     Increase brightness by 10%"
echo -e "  ${COLOR_CYAN}brightpanel doctor${COLOR_RESET}     Run system diagnostics"
echo ""
