#!/usr/bin/env bash
# ==============================================================================
# BrightPanel - Uninstaller for Fedora Linux
# ==============================================================================

set -e

COLOR_CYAN='\033[1;36m'
COLOR_GREEN='\033[1;32m'
COLOR_RED='\033[1;31m'
COLOR_RESET='\033[0m'

TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)

echo -e "${COLOR_CYAN}Uninstalling BrightPanel...${COLOR_RESET}"

# Stop systemd service
sudo -u "$TARGET_USER" systemctl --user disable --now brightpanel.service 2>/dev/null || true
rm -f "$TARGET_HOME/.config/systemd/user/brightpanel.service"

# Remove GNOME extension
if command -v gnome-extensions > /dev/null 2>&1; then
    sudo -u "$TARGET_USER" gnome-extensions disable brightpanel@subhadipshil.github.com 2>/dev/null || true
fi
rm -rf "$TARGET_HOME/.local/share/gnome-shell/extensions/brightpanel@subhadipshil.github.com"

# Remove desktop file and icons
sudo rm -f /usr/share/applications/io.github.subhadipshil.brightpanel.desktop
sudo rm -f /usr/share/metainfo/io.github.subhadipshil.brightpanel.metainfo.xml
sudo rm -f /usr/share/icons/hicolor/scalable/apps/io.github.subhadipshil.brightpanel.svg

if command -v update-desktop-database > /dev/null 2>&1; then
    sudo update-desktop-database /usr/share/applications > /dev/null 2>&1 || true
fi

# Remove python package & binaries
sudo pip3 uninstall -y brightpanel 2>/dev/null || true
sudo rm -f /usr/local/bin/brightpanel /usr/local/bin/brightpanel-gui

echo -e "${COLOR_GREEN}BrightPanel has been successfully removed.${COLOR_RESET}"
