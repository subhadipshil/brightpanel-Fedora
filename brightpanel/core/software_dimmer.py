"""Software dimming and gamma compensation fallback for displays without DDC/CI support."""

from __future__ import annotations
import shutil
import subprocess
import logging
from typing import Optional

logger = logging.getLogger("brightpanel.software_dimmer")


class SoftwareDimmer:
    """Provides software-based brightness control via gamma LUT / xrandr / compositor."""

    def __init__(self):
        self.has_xrandr = shutil.which("xrandr") is not None

    def apply_software_brightness(self, connector: str, percentage: int) -> bool:
        """Applies software brightness scaling (0.1 to 1.0) for a display connector.

        Used as a fallback when monitor hardware DDC/CI is unavailable.
        """
        pct = max(10, min(100, percentage))
        gamma_factor = pct / 100.0

        if self.has_xrandr and connector and connector != "Unknown":
            try:
                cmd = ["xrandr", "--output", connector, "--brightness", f"{gamma_factor:.2f}"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    logger.debug("Applied xrandr software brightness %s to %s", gamma_factor, connector)
                    return True
            except Exception as e:
                logger.debug("xrandr software brightness failed: %s", e)

        return False
