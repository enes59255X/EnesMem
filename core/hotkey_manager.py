"""
hotkey_manager.py — Global hotkey management using pynput.
Works even when the application is in background.
"""
from typing import Callable, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum, auto
import json
import os

from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from utils.logger import log
from utils.settings import settings


class HotkeyAction(Enum):
    """Predefined actions for hotkeys."""
    TOGGLE_FREEZE_ALL = auto()
    UNFREEZE_ALL = auto()
    INCREASE_VALUE = auto()
    DECREASE_VALUE = auto()
    TOGGLE_WINDOW = auto()
    RUN_SCRIPT = auto()
    ATTACH_PROCESS = auto()
    DETACH_PROCESS = auto()
    NEXT_SCAN = auto()
    RESET_SCAN = auto()


@dataclass
class HotkeyConfig:
    """Configuration for a single hotkey."""
    key_combination: str  # e.g., "<ctrl>+<shift>+f1"
    action: HotkeyAction
    description: str
    enabled: bool = True
    params: Optional[dict] = None  # Extra parameters for actions
    
    def to_dict(self) -> dict:
        return {
            "key_combination": self.key_combination,
            "action": self.action.name,
            "description": self.description,
            "enabled": self.enabled,
            "params": self.params or {}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "HotkeyConfig":
        return cls(
            key_combination=data.get("key_combination", ""),
            action=HotkeyAction[data.get("action", "TOGGLE_FREEZE_ALL")],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            params=data.get("params", {})
        )


class HotkeyManager(QObject):
    """
    Global hotkey manager using pynput.
    Works globally (even when app is not focused).
    
    Signals:
        sig_action_triggered(action, params): Emitted when a hotkey is pressed
        sig_hotkey_added(key_combo, action): Emitted when hotkey is registered
        sig_hotkey_removed(key_combo): Emitted when hotkey is unregistered
    """
    sig_action_triggered = pyqtSignal(object, object)  # HotkeyAction, params
    sig_hotkey_added = pyqtSignal(str, object)  # key_combo, HotkeyAction
    sig_hotkey_removed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hotkeys: Dict[str, HotkeyConfig] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._is_running = False
        self._config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "data", "hotkeys.json"
        )
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        
        # Load default hotkeys if none exist
        self._load_defaults()
    
    def _load_defaults(self) -> None:
        """Load default hotkey configuration."""
        defaults = [
            HotkeyConfig("<ctrl>+<f1>", HotkeyAction.TOGGLE_FREEZE_ALL, "Tüm değerleri dondur/aç"),
            HotkeyConfig("<ctrl>+<f2>", HotkeyAction.UNFREEZE_ALL, "Tüm dondurmaları kaldır"),
            HotkeyConfig("<ctrl>+<f3>", HotkeyAction.TOGGLE_WINDOW, "Pencereyi göster/gizle"),
            HotkeyConfig("<ctrl>+<f5>", HotkeyAction.NEXT_SCAN, "Sonraki tarama"),
            HotkeyConfig("<ctrl>+<f6>", HotkeyAction.RESET_SCAN, "Taramayı sıfırla"),
        ]
        
        for hk in defaults:
            if hk.key_combination not in self._hotkeys:
                self._hotkeys[hk.key_combination] = hk
    
    def start(self) -> bool:
        """Start the global hotkey listener."""
        if self._is_running:
            return True
        
        try:
            # Build hotkey dictionary for pynput
            hotkey_map = {}
            for key_combo, config in self._hotkeys.items():
                if config.enabled:
                    hotkey_map[key_combo] = self._make_callback(key_combo)
            
            if hotkey_map:
                self._listener = keyboard.GlobalHotKeys(hotkey_map)
                self._listener.start()
            
            self._is_running = True
            log.info("HotkeyManager: Global hotkeys started (%d active)", len(hotkey_map))
            return True
            
        except Exception as e:
            log.error("HotkeyManager: Failed to start: %s", e)
            self.sig_error.emit(f"Global hotkey başlatılamadı: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the global hotkey listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception as e:
                log.debug("HotkeyManager: Stop error: %s", e)
            self._listener = None
        
        self._is_running = False
        log.info("HotkeyManager: Global hotkeys stopped")
    
    def _make_callback(self, key_combo: str) -> Callable:
        """Create a callback for a specific hotkey."""
        def callback():
            try:
                config = self._hotkeys.get(key_combo)
                if config and config.enabled:
                    log.debug("Hotkey triggered: %s -> %s", key_combo, config.action.name)
                    self.sig_action_triggered.emit(config.action, config.params or {})
            except Exception as e:
                log.error("Hotkey callback error: %s", e)
        
        return callback
    
    def add_hotkey(self, key_combo: str, action: HotkeyAction, 
                   description: str = "", params: Optional[dict] = None) -> bool:
        """
        Add a new global hotkey.
        
        Args:
            key_combo: Key combination string (e.g., "<ctrl>+f1", "<alt>+<shift>+a")
            action: The action to trigger
            description: Human-readable description
            params: Optional parameters for the action
        
        Returns:
            True if successfully added
        """
        try:
            # Validate key combination format
            if not self._validate_key_combo(key_combo):
                return False
            
            # Check for conflicts
            if key_combo in self._hotkeys:
                log.warning("HotkeyManager: Overwriting existing hotkey: %s", key_combo)
            
            config = HotkeyConfig(
                key_combination=key_combo,
                action=action,
                description=description,
                enabled=True,
                params=params
            )
            
            self._hotkeys[key_combo] = config
            
            # Restart listener to include new hotkey
            if self._is_running:
                self.stop()
                self.start()
            
            self.sig_hotkey_added.emit(key_combo, action)
            log.info("HotkeyManager: Added %s -> %s", key_combo, action.name)
            return True
            
        except Exception as e:
            log.error("HotkeyManager: Failed to add hotkey: %s", e)
            return False
    
    def remove_hotkey(self, key_combo: str) -> bool:
        """Remove a global hotkey."""
        if key_combo not in self._hotkeys:
            return False
        
        del self._hotkeys[key_combo]
        
        # Restart listener
        if self._is_running:
            self.stop()
            self.start()
        
        self.sig_hotkey_removed.emit(key_combo)
        log.info("HotkeyManager: Removed %s", key_combo)
        return True
    
    def set_enabled(self, key_combo: str, enabled: bool) -> bool:
        """Enable or disable a hotkey without removing it."""
        if key_combo not in self._hotkeys:
            return False
        
        self._hotkeys[key_combo].enabled = enabled
        
        # Restart to apply changes
        if self._is_running:
            self.stop()
            self.start()
        
        return True
    
    def get_all_hotkeys(self) -> List[HotkeyConfig]:
        """Get list of all configured hotkeys."""
        return list(self._hotkeys.values())
    
    def get_hotkey(self, key_combo: str) -> Optional[HotkeyConfig]:
        """Get configuration for a specific hotkey."""
        return self._hotkeys.get(key_combo)
    
    def _validate_key_combo(self, key_combo: str) -> bool:
        """Validate key combination format."""
        try:
            # Basic validation - pynput will do the real validation
            if not key_combo or len(key_combo) < 2:
                return False
            
            # Must have at least one modifier or be a function key
            has_modifier = any(m in key_combo.lower() for m in ['<ctrl>', '<alt>', '<shift>', '<cmd>'])
            has_key = len(key_combo.replace('<', '').replace('>', '').replace('+', '')) > 0
            
            return has_modifier or has_key
            
        except Exception:
            return False
    
    def save_config(self) -> bool:
        """Save hotkey configuration to file."""
        try:
            data = {
                "hotkeys": [hk.to_dict() for hk in self._hotkeys.values()]
            }
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            log.info("HotkeyManager: Configuration saved to %s", self._config_path)
            return True
            
        except Exception as e:
            log.error("HotkeyManager: Failed to save config: %s", e)
            return False
    
    def load_config(self) -> bool:
        """Load hotkey configuration from file."""
        try:
            if not os.path.exists(self._config_path):
                log.info("HotkeyManager: No config file found, using defaults")
                return True
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Clear existing hotkeys
            self._hotkeys.clear()
            
            # Load from file
            for hk_data in data.get("hotkeys", []):
                try:
                    hk = HotkeyConfig.from_dict(hk_data)
                    self._hotkeys[hk.key_combination] = hk
                except Exception as e:
                    log.warning("HotkeyManager: Failed to load hotkey: %s", e)
            
            # Add defaults if missing
            self._load_defaults()
            
            log.info("HotkeyManager: Configuration loaded (%d hotkeys)", len(self._hotkeys))
            return True
            
        except Exception as e:
            log.error("HotkeyManager: Failed to load config: %s", e)
            return False
    
    def is_running(self) -> bool:
        """Check if hotkey listener is active."""
        return self._is_running


# Global instance
hotkey_manager = HotkeyManager()
