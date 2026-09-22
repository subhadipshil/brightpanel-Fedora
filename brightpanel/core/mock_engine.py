"""High-fidelity virtual DDC/CI monitor simulator for testing, CI, and demonstration."""

from __future__ import annotations
from typing import List, Dict, Any, Optional

from brightpanel.core.detector import DisplayInfo
from brightpanel.core.vcp_manager import VCPCode


class MockMonitorEngine:
    """Simulates external monitor hardware responses and state transitions."""

    def __init__(self):
        self.monitors: Dict[int, DisplayInfo] = {
            1: DisplayInfo(
                id="mock-disp-1",
                display_num=1,
                bus_num=4,
                model="Dell UltraSharp U2723QE",
                mfg_id="DEL",
                serial="CN-0P826F-74445",
                connector="DP-1",
                is_internal=False,
                is_ddc_supported=True,
                current_brightness=75,
                current_contrast=70,
                current_volume=40,
                current_input=0x0F,  # DisplayPort 1
                is_mock=True
            ),
            2: DisplayInfo(
                id="mock-disp-2",
                display_num=2,
                bus_num=5,
                model="LG UltraFine 27MD5KL",
                mfg_id="GSM",
                serial="108NTXF9K219",
                connector="HDMI-1",
                is_internal=False,
                is_ddc_supported=True,
                current_brightness=50,
                current_contrast=50,
                current_volume=65,
                current_input=0x11,  # HDMI 1
                is_mock=True
            )
        }

    def get_monitors(self) -> List[DisplayInfo]:
        return list(self.monitors.values())

    def get_monitor(self, display_num: int) -> Optional[DisplayInfo]:
        return self.monitors.get(display_num)

    def set_vcp(self, display_num: int, vcp_code: int, value: int) -> bool:
        mon = self.monitors.get(display_num)
        if not mon:
            return False

        val = max(0, min(100, value))
        if vcp_code == VCPCode.BRIGHTNESS:
            mon.current_brightness = val
        elif vcp_code == VCPCode.CONTRAST:
            mon.current_contrast = val
        elif vcp_code == VCPCode.AUDIO_VOLUME:
            mon.current_volume = val
        elif vcp_code == VCPCode.INPUT_SOURCE:
            mon.current_input = value
        return True
