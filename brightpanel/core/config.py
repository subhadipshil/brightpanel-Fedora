"""Configuration storage and user preferences management."""

from __future__ import annotations
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

from brightpanel.core.vcp_manager import DEFAULT_PRESETS

logger = logging.getLogger("brightpanel.config")


@dataclass
class ConfigData:
    sync_all: bool = False
    step_size: int = 5
    debounce_ms: int = 100
    smooth_transitions: bool = True
    enable_tray: bool = True
    presets: Dict[str, Dict[str, int]] = field(default_factory=lambda: dict(DEFAULT_PRESETS))
    display_names: Dict[str, str] = field(default_factory=dict)
    night_mode_enabled: bool = False
    night_start: str = "21:00"
    day_start: str = "07:00"
    night_preset: str = "night"
    day_preset: str = "daylight"


class ConfigManager:
    """Handles loading and saving user settings in ~/.config/brightpanel/config.json."""

    def __init__(self, config_dir: str | None = None):
        if config_dir:
            self.config_dir = config_dir
        else:
            base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            self.config_dir = os.path.join(base, "brightpanel")

        self.config_file = os.path.join(self.config_dir, "config.json")
        self.data: ConfigData = self._load()

    def _load(self) -> ConfigData:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    presets = raw.get("presets", {})
                    # Merge with default presets if missing
                    merged_presets = dict(DEFAULT_PRESETS)
                    merged_presets.update(presets)
                    raw["presets"] = merged_presets
                    return ConfigData(**{k: v for k, v in raw.items() if k in ConfigData.__dataclass_fields__})
            except Exception as e:
                logger.error("Failed loading configuration from %s: %s", self.config_file, e)

        return ConfigData()

    def save(self) -> bool:
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self.data), f, indent=2)
            return True
        except Exception as e:
            logger.error("Failed saving configuration to %s: %s", self.config_file, e)
            return False

    def get_preset(self, name: str) -> Dict[str, int] | None:
        return self.data.presets.get(name.lower())

    def set_preset(self, name: str, brightness: int, contrast: int) -> None:
        self.data.presets[name.lower()] = {
            "brightness": max(0, min(100, brightness)),
            "contrast": max(0, min(100, contrast)),
        }
        self.save()
