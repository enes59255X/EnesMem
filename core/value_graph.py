"""
value_graph.py — Value history tracking and graph data management.
Tracks value changes over time for watchlist entries.
"""
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
import json
import os

from utils.patterns import DataType
from utils.logger import log


@dataclass
class ValueDataPoint:
    """Single value data point at a timestamp."""
    timestamp: float
    value: float
    
    def to_dict(self) -> dict:
        return {"t": self.timestamp, "v": self.value}
    
    @classmethod
    def from_dict(cls, data: dict) -> "ValueDataPoint":
        return cls(timestamp=data.get("t", 0), value=data.get("v", 0))


@dataclass
class ValueHistory:
    """History of values for a single address/entry."""
    address: int
    dtype: DataType
    description: str = ""
    max_points: int = 1000
    data_points: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def __post_init__(self):
        if not isinstance(self.data_points, deque):
            self.data_points = deque(self.data_points, maxlen=self.max_points)
    
    def add_value(self, value: float) -> None:
        """Add a new value data point."""
        timestamp = datetime.now().timestamp()
        self.data_points.append(ValueDataPoint(timestamp, value))
    
    def get_data(self) -> List[Tuple[float, float]]:
        """Get all data points as (timestamp, value) tuples."""
        return [(dp.timestamp, dp.value) for dp in self.data_points]
    
    def get_latest(self) -> Optional[ValueDataPoint]:
        """Get the most recent data point."""
        if self.data_points:
            return self.data_points[-1]
        return None
    
    def get_min_max(self) -> Tuple[float, float]:
        """Get min and max values in history."""
        if not self.data_points:
            return (0, 0)
        values = [dp.value for dp in self.data_points]
        return (min(values), max(values))
    
    def clear(self) -> None:
        """Clear all history."""
        self.data_points.clear()
    
    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "dtype": self.dtype.value,
            "description": self.description,
            "data": [dp.to_dict() for dp in self.data_points]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ValueHistory":
        dtype = DataType(data.get("dtype", "4_bytes"))
        history = cls(
            address=data.get("address", 0),
            dtype=dtype,
            description=data.get("description", "")
        )
        for dp_data in data.get("data", []):
            history.data_points.append(ValueDataPoint.from_dict(dp_data))
        return history


class ValueGraphManager:
    """
    Manages value history tracking for multiple addresses.
    Singleton pattern for global access.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._histories: Dict[int, ValueHistory] = {}
            cls._instance._enabled = True
            cls._config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "value_graphs.json"
            )
            os.makedirs(os.path.dirname(cls._instance._config_path), exist_ok=True)
        return cls._instance
    
    def enable_tracking(self) -> None:
        """Enable value tracking."""
        self._enabled = True
        log.info("ValueGraphManager: Tracking enabled")
    
    def disable_tracking(self) -> None:
        """Disable value tracking."""
        self._enabled = False
        log.info("ValueGraphManager: Tracking disabled")
    
    def is_enabled(self) -> bool:
        """Check if tracking is enabled."""
        return self._enabled
    
    def track_value(self, address: int, value: float, dtype: DataType, description: str = "") -> None:
        """Track a value for an address."""
        if not self._enabled:
            return
        
        if address not in self._histories:
            self._histories[address] = ValueHistory(
                address=address,
                dtype=dtype,
                description=description
            )
        
        history = self._histories[address]
        # Update description if provided
        if description:
            history.description = description
        
        history.add_value(value)
    
    def get_history(self, address: int) -> Optional[ValueHistory]:
        """Get value history for an address."""
        return self._histories.get(address)
    
    def get_all_histories(self) -> List[ValueHistory]:
        """Get all value histories."""
        return list(self._histories.values())
    
    def remove_history(self, address: int) -> bool:
        """Remove history for an address."""
        if address in self._histories:
            del self._histories[address]
            return True
        return False
    
    def clear_all(self) -> None:
        """Clear all histories."""
        self._histories.clear()
        log.info("ValueGraphManager: All histories cleared")
    
    def get_tracked_addresses(self) -> List[int]:
        """Get list of all tracked addresses."""
        return list(self._histories.keys())
    
    def save_histories(self) -> bool:
        """Save all histories to file."""
        try:
            data = {
                "histories": [h.to_dict() for h in self._histories.values()]
            }
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            log.info("ValueGraphManager: Saved %d histories", len(self._histories))
            return True
            
        except Exception as e:
            log.error("ValueGraphManager: Save failed: %s", e)
            return False
    
    def load_histories(self) -> bool:
        """Load histories from file."""
        try:
            if not os.path.exists(self._config_path):
                return True
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._histories.clear()
            
            for h_data in data.get("histories", []):
                try:
                    history = ValueHistory.from_dict(h_data)
                    self._histories[history.address] = history
                except Exception as e:
                    log.warning("ValueGraphManager: Failed to load history: %s", e)
            
            log.info("ValueGraphManager: Loaded %d histories", len(self._histories))
            return True
            
        except Exception as e:
            log.error("ValueGraphManager: Load failed: %s", e)
            return False
    
    def export_csv(self, address: int, filepath: str) -> bool:
        """Export history to CSV file."""
        history = self._histories.get(address)
        if not history:
            return False
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Timestamp,Value\n")
                for ts, val in history.get_data():
                    f.write(f"{ts},{val}\n")
            return True
        except Exception as e:
            log.error("ValueGraphManager: CSV export failed: %s", e)
            return False


# Global instance
graph_manager = ValueGraphManager()
