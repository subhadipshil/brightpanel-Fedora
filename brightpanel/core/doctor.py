"""Comprehensive Fedora system diagnostics for DDC/CI and external monitor control."""

from __future__ import annotations
import os
import glob
import shutil
import getpass
try:
    import grp
except ImportError:
    grp = None  # type: ignore
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class DiagnosticItem:
    """Individual diagnostic check result."""
    name: str
    status: str  # "OK", "WARN", "FAIL"
    message: str
    suggestion: Optional[str] = None
    fix_command: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "suggestion": self.suggestion,
            "fix_command": self.fix_command
        }


class SystemDoctor:
    """Audits Fedora system readiness for DDC/CI monitor communication."""

    def __init__(self):
        self.username = getpass.getuser()

    def run_all_checks(self) -> List[DiagnosticItem]:
        """Runs the complete diagnostic suite."""
        results: List[DiagnosticItem] = []
        results.append(self.check_ddcutil_installed())
        results.append(self.check_kernel_module_i2c_dev())
        results.append(self.check_udev_rules())
        results.append(self.check_user_group_membership())
        results.append(self.check_i2c_devices_accessible())
        results.append(self.check_displays_detected())
        return results

    def check_ddcutil_installed(self) -> DiagnosticItem:
        ddcutil_path = shutil.which("ddcutil")
        if ddcutil_path:
            # Check version
            try:
                res = subprocess.run(["ddcutil", "--version"], capture_output=True, text=True, timeout=3)
                first_line = res.stdout.splitlines()[0] if res.stdout else "ddcutil installed"
                return DiagnosticItem(
                    name="ddcutil Binary",
                    status="OK",
                    message=f"Found: {ddcutil_path} ({first_line})"
                )
            except Exception:
                return DiagnosticItem(
                    name="ddcutil Binary",
                    status="OK",
                    message=f"Found: {ddcutil_path}"
                )
        return DiagnosticItem(
            name="ddcutil Binary",
            status="FAIL",
            message="ddcutil is not installed.",
            suggestion="Install ddcutil via DNF package manager.",
            fix_command="sudo dnf install -y ddcutil"
        )

    def check_kernel_module_i2c_dev(self) -> DiagnosticItem:
        # Check /proc/modules or /sys/module/i2c_dev
        is_loaded = os.path.exists("/sys/module/i2c_dev")
        auto_load = os.path.exists("/etc/modules-load.d/i2c-dev.conf")

        if is_loaded:
            if auto_load:
                return DiagnosticItem(
                    name="Kernel Module (i2c-dev)",
                    status="OK",
                    message="i2c-dev module is loaded and configured to load at boot."
                )
            return DiagnosticItem(
                name="Kernel Module (i2c-dev)",
                status="WARN",
                message="i2c-dev is currently loaded, but not configured to persist across reboots.",
                suggestion="Create /etc/modules-load.d/i2c-dev.conf",
                fix_command="echo 'i2c-dev' | sudo tee /etc/modules-load.d/i2c-dev.conf"
            )

        return DiagnosticItem(
            name="Kernel Module (i2c-dev)",
            status="FAIL",
            message="i2c-dev kernel module is not loaded.",
            suggestion="Load the module now and enable boot loading.",
            fix_command="sudo modprobe i2c-dev && echo 'i2c-dev' | sudo tee /etc/modules-load.d/i2c-dev.conf"
        )

    def check_udev_rules(self) -> DiagnosticItem:
        rules_paths = [
            "/etc/udev/rules.d/45-ddcutil-i2c.rules",
            "/usr/lib/udev/rules.d/60-ddcutil-i2c.rules",
            "/etc/udev/rules.d/60-ddcutil-i2c.rules"
        ]
        found = [p for p in rules_paths if os.path.exists(p)]
        if found:
            return DiagnosticItem(
                name="udev Permissions Rules",
                status="OK",
                message=f"Found udev rule: {found[0]}"
            )

        return DiagnosticItem(
            name="udev Permissions Rules",
            status="WARN",
            message="No specific ddcutil udev rule found in /etc/udev/rules.d/.",
            suggestion="Install 45-ddcutil-i2c.rules to grant non-root access.",
            fix_command="sudo cp packaging/45-ddcutil-i2c.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger"
        )

    def check_user_group_membership(self) -> DiagnosticItem:
        if grp is None:
            return DiagnosticItem(
                name="User Group (i2c)",
                status="OK",
                message="Linux grp module not available (running in simulation/non-Linux mode)."
            )
        try:
            i2c_grp = grp.getgrnam("i2c")
            if self.username in i2c_grp.gr_mem:
                return DiagnosticItem(
                    name="User Group (i2c)",
                    status="OK",
                    message=f"User '{self.username}' is a member of the 'i2c' group."
                )
            return DiagnosticItem(
                name="User Group (i2c)",
                status="FAIL",
                message=f"User '{self.username}' is not in the 'i2c' group.",
                suggestion="Add user to i2c group (requires logout/re-login).",
                fix_command=f"sudo usermod -aG i2c {self.username}"
            )
        except KeyError:
            # i2c group does not exist
            return DiagnosticItem(
                name="User Group (i2c)",
                status="WARN",
                message="The 'i2c' group does not exist on this system.",
                suggestion="Create i2c group and add current user.",
                fix_command=f"sudo groupadd -f i2c && sudo usermod -aG i2c {self.username}"
            )
        except Exception as e:
            return DiagnosticItem(
                name="User Group (i2c)",
                status="WARN",
                message=f"Could not verify group membership: {e}"
            )

    def check_i2c_devices_accessible(self) -> DiagnosticItem:
        devices = glob.glob("/dev/i2c-*")
        if not devices:
            return DiagnosticItem(
                name="I2C Device Nodes (/dev/i2c-*)",
                status="FAIL",
                message="No /dev/i2c-* device nodes exist. Module i2c-dev may not be loaded.",
                suggestion="Load i2c-dev kernel module.",
                fix_command="sudo modprobe i2c-dev"
            )

        readable = [d for d in devices if os.access(d, os.R_OK | os.W_OK)]
        if readable:
            return DiagnosticItem(
                name="I2C Device Nodes (/dev/i2c-*)",
                status="OK",
                message=f"{len(readable)} of {len(devices)} I2C device nodes are read/write accessible."
            )

        return DiagnosticItem(
            name="I2C Device Nodes (/dev/i2c-*)",
            status="FAIL",
            message=f"Found {len(devices)} I2C devices, but none are writable by user '{self.username}'.",
            suggestion="Reload udev rules and verify group membership.",
            fix_command="sudo udevadm control --reload-rules && sudo udevadm trigger"
        )

    def check_displays_detected(self) -> DiagnosticItem:
        if not shutil.which("ddcutil"):
            return DiagnosticItem(
                name="Connected Displays (DDC/CI)",
                status="WARN",
                message="Skipped: ddcutil is not installed."
            )

        try:
            res = subprocess.run(["ddcutil", "detect", "--brief"], capture_output=True, text=True, timeout=8)
            if "Display" in res.stdout:
                count = res.stdout.count("Display ")
                return DiagnosticItem(
                    name="Connected Displays (DDC/CI)",
                    status="OK",
                    message=f"Detected {count} display(s) communicating via DDC/CI."
                )
            else:
                return DiagnosticItem(
                    name="Connected Displays (DDC/CI)",
                    status="WARN",
                    message="No external displays responded to DDC/CI probes.",
                    suggestion="Ensure DDC/CI is turned ON in your monitor's physical button menu (OSD)."
                )
        except Exception as e:
            return DiagnosticItem(
                name="Connected Displays (DDC/CI)",
                status="WARN",
                message=f"Display probe error: {e}"
            )

    def generate_cli_report(self) -> str:
        """Generates ANSI color-formatted CLI diagnostic report."""
        checks = self.run_all_checks()
        lines = [
            "\033[1;36m=====================================================\033[0m",
            "\033[1;36m       BrightPanel System Doctor - Fedora Audit       \033[0m",
            "\033[1;36m=====================================================\033[0m",
            ""
        ]

        has_failures = False
        for c in checks:
            if c.status == "OK":
                badge = "\033[1;32m[PASS]\033[0m"
            elif c.status == "WARN":
                badge = "\033[1;33m[WARN]\033[0m"
            else:
                badge = "\033[1;31m[FAIL]\033[0m"
                has_failures = True

            lines.append(f"{badge} \033[1m{c.name}\033[0m")
            lines.append(f"       {c.message}")
            if c.suggestion:
                lines.append(f"       \033[33mSuggestion: {c.suggestion}\033[0m")
            if c.fix_command:
                lines.append(f"       \033[36mQuick Fix:  {c.fix_command}\033[0m")
            lines.append("")

        if has_failures:
            lines.append("\033[1;31mSome checks failed. Run 'brightpanel setup' to configure permissions automatically.\033[0m")
        else:
            lines.append("\033[1;32mAll core system checks passed! External monitor controls ready.\033[0m")

        return "\n".join(lines)
