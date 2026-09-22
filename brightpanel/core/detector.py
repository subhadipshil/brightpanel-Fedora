"""Hardware display detection engine supporting DDC/CI (via ddcutil) and DRM/Sysfs."""

from __future__ import annotations
import os
import re
import shutil
import subprocess
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from brightpanel.core.vcp_manager import VCPCode

logger = logging.getLogger("brightpanel.detector")


@dataclass
class DisplayInfo:
    """Represents a connected physical or virtual display."""
    id: str
    display_num: int
    bus_num: int
    model: str
    mfg_id: str = "Unknown"
    serial: str = "Unknown"
    connector: str = "Unknown"
    is_internal: bool = False
    is_ddc_supported: bool = True
    current_brightness: int = 50
    current_contrast: int = 50
    current_volume: int = 30
    current_input: int = 0x11
    max_brightness: int = 100
    max_contrast: int = 100
    is_mock: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        if self.model and self.model != "Unknown":
            return self.model
        if self.connector and self.connector != "Unknown":
            return f"Display ({self.connector})"
        return f"External Monitor #{self.display_num}"

    @property
    def summary(self) -> str:
        bus_str = f"/dev/i2c-{self.bus_num}" if self.bus_num >= 0 else "N/A"
        return f"[{self.display_num}] {self.display_name} ({self.connector}, {bus_str}) - {self.current_brightness}%"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["display_name"] = self.display_name
        return d


class DisplayDetector:
    """Scans and detects external monitors using ddcutil with fallback to mock/sysfs."""

    def __init__(self, ddcutil_bin: Optional[str] = None):
        self.ddcutil_bin = ddcutil_bin or shutil.which("ddcutil") or "ddcutil"
        self._cache: List[DisplayInfo] = []

    def is_ddcutil_available(self) -> bool:
        return shutil.which(self.ddcutil_bin) is not None

    def detect(self, force_refresh: bool = False, allow_mock: bool = False) -> List[DisplayInfo]:
        """Detects connected monitors.

        Args:
            force_refresh: If False, returns cached results if available.
            allow_mock: If True or if MOCK_DDC environment variable is set, returns simulated displays
                        when no physical DDC/CI monitor is found.
        """
        if self._cache and not force_refresh:
            return self._cache

        use_mock = allow_mock or os.environ.get("MOCK_DDC", "0") in ("1", "true", "yes")

        displays: List[DisplayInfo] = []

        if self.is_ddcutil_available() and not use_mock:
            displays = self._detect_via_ddcutil()

        # Check internal laptop display via backlight sysfs
        internal = self._detect_internal_display()
        if internal:
            displays.append(internal)

        if not displays and use_mock:
            logger.info("No physical DDC/CI monitors found or mock requested; initializing mock displays.")
            displays = self._get_mock_displays()

        self._cache = displays
        return displays

    def _detect_via_ddcutil(self) -> List[DisplayInfo]:
        """Runs 'ddcutil detect --brief' or 'ddcutil detect' and parses output."""
        try:
            cmd = [self.ddcutil_bin, "detect"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=12,
                check=False
            )
            if result.returncode == 0 and result.stdout:
                return self._parse_ddcutil_output(result.stdout)
            else:
                logger.warning("ddcutil detect returned code %d: %s", result.returncode, result.stderr)
        except subprocess.TimeoutExpired:
            logger.error("ddcutil detect timed out after 12s.")
        except Exception as e:
            logger.error("Error executing ddcutil detect: %s", e)

        return []

    def _parse_ddcutil_output(self, output: str) -> List[DisplayInfo]:
        """Parses output from 'ddcutil detect'."""
        displays: List[DisplayInfo] = []
        matches = re.findall(
            r"(?:^|\n)Display\s+(\d+)([\s\S]*?)(?=(?:\nDisplay\s+\d+|\nInvalid display|\Z))",
            output
        )

        for match in matches:
            display_num = int(match[0])
            block = match[1]

            # Skip if communication failed or no controls
            if "Controls: None" in block:
                continue

            # Extract I2C bus
            bus_match = re.search(r"I2C bus:\s+/dev/i2c-(\d+)", block)
            bus_num = int(bus_match.group(1)) if bus_match else -1

            # Extract DRM connector
            conn_match = re.search(r"DRM connector:\s+([^\n]+)", block)
            connector = conn_match.group(1).strip() if conn_match else "Unknown"

            # Extract Mfg id
            mfg_match = re.search(r"Mfg id:\s+([^\n]+)", block)
            mfg_id = mfg_match.group(1).strip() if mfg_match else "Unknown"

            # Extract Model
            model_match = re.search(r"Model:\s+([^\n]+)", block)
            model = model_match.group(1).strip() if model_match else f"Display {display_num}"

            # Extract Serial
            serial_match = re.search(r"Serial number:\s+([^\n]+)", block)
            serial = serial_match.group(1).strip() if serial_match else "Unknown"

            # Check DDC/CI support
            is_ddc = "DDC communication failed" not in block

            disp = DisplayInfo(
                id=f"ddc-{display_num}-i2c-{bus_num}",
                display_num=display_num,
                bus_num=bus_num,
                model=model,
                mfg_id=mfg_id,
                serial=serial,
                connector=connector,
                is_ddc_supported=is_ddc,
                is_internal=False,
                is_mock=False
            )

            # Fetch initial brightness & contrast
            self._populate_current_values(disp)
            displays.append(disp)

        return displays

    def _populate_current_values(self, disp: DisplayInfo) -> None:
        """Fetches current brightness and contrast using ddcutil getvcp."""
        if not self.is_ddcutil_available() or not disp.is_ddc_supported or disp.display_num <= 0:
            return

        try:
            # Query brightness (0x10)
            cmd = [self.ddcutil_bin, "getvcp", "10", "--display", str(disp.display_num), "--brief"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                # brief output format: VCP 10 C 50 100
                m = re.search(r"VCP\s+10\s+[A-Z]\s+(\d+)\s+(\d+)", res.stdout)
                if m:
                    disp.current_brightness = int(m.group(1))
                    disp.max_brightness = int(m.group(2)) or 100

            # Query contrast (0x12)
            cmd_c = [self.ddcutil_bin, "getvcp", "12", "--display", str(disp.display_num), "--brief"]
            res_c = subprocess.run(cmd_c, capture_output=True, text=True, timeout=5)
            if res_c.returncode == 0:
                m_c = re.search(r"VCP\s+12\s+[A-Z]\s+(\d+)\s+(\d+)", res_c.stdout)
                if m_c:
                    disp.current_contrast = int(m_c.group(1))
                    disp.max_contrast = int(m_c.group(2)) or 100
        except Exception as e:
            logger.debug("Could not fetch current VCP values for %s: %s", disp.display_name, e)

    def _detect_internal_display(self) -> Optional[DisplayInfo]:
        """Checks for internal laptop panel via /sys/class/backlight."""
        backlight_dir = "/sys/class/backlight"
        if not os.path.exists(backlight_dir):
            return None

        try:
            entries = os.listdir(backlight_dir)
            if not entries:
                return None

            device = entries[0]
            dev_path = os.path.join(backlight_dir, device)
            actual_file = os.path.join(dev_path, "brightness")
            max_file = os.path.join(dev_path, "max_brightness")

            if os.path.exists(actual_file) and os.path.exists(max_file):
                with open(actual_file, "r") as f:
                    curr_raw = int(f.read().strip())
                with open(max_file, "r") as f:
                    max_raw = int(f.read().strip())

                pct = int((curr_raw / max_raw) * 100) if max_raw > 0 else 50
                return DisplayInfo(
                    id=f"internal-{device}",
                    display_num=0,
                    bus_num=-1,
                    model=f"Internal Display ({device})",
                    mfg_id="Internal",
                    connector="eDP-1",
                    is_internal=True,
                    is_ddc_supported=False,
                    current_brightness=pct,
                    max_brightness=100,
                    extra={"sysfs_path": dev_path, "max_raw": max_raw}
                )
        except Exception as e:
            logger.debug("Error checking internal backlight: %s", e)

        return None

    def _get_mock_displays(self) -> List[DisplayInfo]:
        """Provides simulated dual external monitors for testing and demonstrations."""
        return [
            DisplayInfo(
                id="mock-disp-1",
                display_num=1,
                bus_num=4,
                model="Dell UltraSharp U2723QE (Mock)",
                mfg_id="DEL",
                serial="CN-0P826F-74445",
                connector="card0-DP-1",
                is_internal=False,
                is_ddc_supported=True,
                current_brightness=75,
                current_contrast=70,
                current_volume=40,
                current_input=0x0F,  # DP-1
                is_mock=True
            ),
            DisplayInfo(
                id="mock-disp-2",
                display_num=2,
                bus_num=5,
                model="LG UltraFine 4K 27MD5KL (Mock)",
                mfg_id="GSM",
                serial="108NTXF9K219",
                connector="card0-HDMI-A-1",
                is_internal=False,
                is_ddc_supported=True,
                current_brightness=50,
                current_contrast=50,
                current_volume=65,
                current_input=0x11,  # HDMI-1
                is_mock=True
            ),
        ]
