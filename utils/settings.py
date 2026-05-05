"""
settings.py — Persistent configuration manager.
Handles language, refresh rates, and other user preferences.
"""
import json
import os
from PyQt5.QtCore import QSettings

class SettingsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_settings()
        return cls._instance

    def _init_settings(self):
        # Using native QSettings (Registry on Windows, .plist on macOS, etc.)
        self._qs = QSettings("EnesMem", "EnesMemApp")
        
        # Default values
        self._defaults = {
            "language": "tr", 
            "refresh_interval_ms": 500,
            "theme": "dark",
            "safe_scan": False,
            "chunk_size": 1024 * 1024, # 1MB
        }

    def get(self, key: str, default=None):
        if default is None:
            default = self._defaults.get(key)
        return self._qs.value(key, default)

    def set(self, key: str, value):
        self._qs.setValue(key, value)

    # Helper methods to match current usage in dialogs
    def get_language(self) -> str:
        return str(self.get("language"))

    def set_language(self, val: str):
        self.set("language", val)

    @property
    def language(self) -> str:
        return self.get_language()

    @language.setter
    def language(self, val: str):
        self.set_language(val)

    @property
    def theme(self) -> str:
        return str(self.get("theme"))

    @theme.setter
    def theme(self, val: str):
        self.set("theme", val)

    @property
    def safe_scan(self) -> bool:
        val = self.get("safe_scan")
        return str(val).lower() == "true" if isinstance(val, str) else bool(val)

    @safe_scan.setter
    def safe_scan(self, val: bool):
        self.set("safe_scan", val)

    @property
    def refresh_interval(self) -> int:
        return int(self.get("refresh_interval_ms"))

    @refresh_interval.setter
    def refresh_interval(self, val: int):
        self.set("refresh_interval_ms", val)

# Global instance
settings = SettingsManager()
