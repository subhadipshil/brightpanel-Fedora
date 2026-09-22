"""Virtual Control Panel (VCP) MCCS feature codes and helper utilities for DDC/CI."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


class VCPCode:
    """Standard VESA MCCS (Monitor Control Command Set) VCP feature codes."""
    BRIGHTNESS = 0x10
    CONTRAST = 0x12
    COLOR_PRESET = 0x14
    RED_GAIN = 0x16
    GREEN_GAIN = 0x18
    BLUE_GAIN = 0x1A
    AUTO_SETUP = 0x1E
    AUDIO_VOLUME = 0x62
    AUDIO_MUTE = 0x8D
    INPUT_SOURCE = 0x60
    POWER_MODE = 0xD6
    OSD_LANGUAGE = 0xCC


class PowerMode:
    """Power mode VCP 0xD6 states."""
    ON = 0x01
    STANDBY = 0x02
    SUSPEND = 0x03
    OFF_SOFT = 0x04
    OFF_HARD = 0x05

    NAMES = {
        ON: "On",
        STANDBY: "Standby",
        SUSPEND: "Suspend",
        OFF_SOFT: "Soft Off",
        OFF_HARD: "Hard Off",
    }


INPUT_SOURCES: Dict[int, str] = {
    0x01: "VGA / Analog 1",
    0x02: "VGA / Analog 2",
    0x03: "DVI 1",
    0x04: "DVI 2",
    0x05: "Composite 1",
    0x0F: "DisplayPort 1",
    0x10: "DisplayPort 2",
    0x11: "HDMI 1",
    0x12: "HDMI 2",
    0x13: "HDMI 3",
    0x1B: "USB-C / DisplayPort",
    0x1C: "USB-C 2",
}

INPUT_NAME_TO_CODE: Dict[str, int] = {
    "hdmi1": 0x11,
    "hdmi2": 0x12,
    "hdmi3": 0x13,
    "dp1": 0x0F,
    "dp2": 0x10,
    "usbc": 0x1B,
    "usb-c": 0x1B,
    "type-c": 0x1B,
    "dvi1": 0x03,
    "vga1": 0x01,
}

DEFAULT_PRESETS: Dict[str, Dict[str, int]] = {
    "daylight": {"brightness": 100, "contrast": 75},
    "office": {"brightness": 75, "contrast": 70},
    "coding": {"brightness": 55, "contrast": 65},
    "reading": {"brightness": 35, "contrast": 50},
    "night": {"brightness": 15, "contrast": 45},
    "minimal": {"brightness": 5, "contrast": 35},
}


@dataclass
class VCPValue:
    """Represents a VCP feature value with current and max values."""
    code: int
    current: int
    max_value: int = 100

    @property
    def percentage(self) -> int:
        if self.max_value <= 0:
            return 0
        return max(0, min(100, int((self.current / self.max_value) * 100)))

    @classmethod
    def clamp(cls, value: int, min_val: int = 0, max_val: int = 100) -> int:
        return max(min_val, min(max_val, int(value)))


def normalize_input_code(user_input: str | int) -> Optional[int]:
    """Converts user input string (e.g. 'hdmi1', 'dp1', '0x11') to VCP integer code."""
    if isinstance(user_input, int):
        return user_input
    clean = user_input.strip().lower()
    if clean.startswith("0x"):
        try:
            return int(clean, 16)
        except ValueError:
            return None
    if clean.isdigit():
        return int(clean)
    return INPUT_NAME_TO_CODE.get(clean)


def get_input_name(code: int) -> str:
    """Returns human-readable name for an input source code."""
    return INPUT_SOURCES.get(code, f"Input (0x{code:02X})")
