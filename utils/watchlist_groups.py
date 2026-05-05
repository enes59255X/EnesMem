"""
watchlist_groups.py — Watchlist grouping and color management.
"""
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from PyQt5.QtGui import QColor

from utils.logger import log


class GroupColor(Enum):
    """Predefined group colors."""
    RED = "#e94560"
    GREEN = "#3fb950"
    BLUE = "#58a6ff"
    YELLOW = "#d29922"
    PURPLE = "#bc8cff"
    ORANGE = "#fdac54"
    CYAN = "#39c5cf"
    PINK = "#f778ba"
    GRAY = "#8b949e"
    WHITE = "#c9d1d9"


@dataclass
class WatchlistGroup:
    """A group/container for watchlist entries."""
    name: str
    color: str = GroupColor.BLUE.value
    expanded: bool = True
    entries_indices: List[int] = field(default_factory=list)  # Indices into main watchlist
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "expanded": self.expanded,
            "entries_indices": self.entries_indices,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WatchlistGroup":
        return cls(
            name=data.get("name", "Unnamed"),
            color=data.get("color", GroupColor.BLUE.value),
            expanded=data.get("expanded", True),
            entries_indices=data.get("entries_indices", []),
            description=data.get("description", "")
        )


class WatchlistGroupManager:
    """
    Manages watchlist groups and their relationships.
    Groups are stored separately and reference watchlist entries by index.
    """
    
    def __init__(self) -> None:
        self._groups: List[WatchlistGroup] = []
        self._default_group: Optional[WatchlistGroup] = None
        self._config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "watchlist_groups.json"
        )
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        
        # Create default group
        self._create_default_group()
    
    def _create_default_group(self) -> None:
        """Create the default 'Ungrouped' group."""
        self._default_group = WatchlistGroup(
            name="Genel",
            color=GroupColor.GRAY.value,
            expanded=True,
            description="Gruplandırılmamış girişler"
        )
    
    def create_group(self, name: str, color: str = None, description: str = "") -> WatchlistGroup:
        """Create a new group."""
        if color is None:
            color = GroupColor.BLUE.value
        
        group = WatchlistGroup(
            name=name,
            color=color,
            expanded=True,
            description=description
        )
        
        self._groups.append(group)
        log.info("WatchlistGroupManager: Created group '%s'", name)
        return group
    
    def remove_group(self, group: WatchlistGroup, move_to_default: bool = True) -> None:
        """Remove a group and optionally move entries to default."""
        if group in self._groups:
            if move_to_default and group.entries_indices:
                # Move entries to default group
                self._default_group.entries_indices.extend(group.entries_indices)
            
            self._groups.remove(group)
            log.info("WatchlistGroupManager: Removed group '%s'", group.name)
    
    def get_all_groups(self) -> List[WatchlistGroup]:
        """Get all groups including default."""
        return [self._default_group] + self._groups
    
    def get_group(self, name: str) -> Optional[WatchlistGroup]:
        """Find group by name."""
        if name == self._default_group.name:
            return self._default_group
        
        for g in self._groups:
            if g.name == name:
                return g
        return None
    
    def add_entry_to_group(self, entry_index: int, group: WatchlistGroup) -> None:
        """Add a watchlist entry to a group."""
        # Remove from current group first
        self.remove_entry_from_all_groups(entry_index)
        
        # Add to new group
        if entry_index not in group.entries_indices:
            group.entries_indices.append(entry_index)
    
    def remove_entry_from_all_groups(self, entry_index: int) -> None:
        """Remove entry from all groups."""
        for group in self.get_all_groups():
            if entry_index in group.entries_indices:
                group.entries_indices.remove(entry_index)
    
    def move_entry(self, entry_index: int, from_group: WatchlistGroup, to_group: WatchlistGroup) -> None:
        """Move entry from one group to another."""
        if entry_index in from_group.entries_indices:
            from_group.entries_indices.remove(entry_index)
        
        if entry_index not in to_group.entries_indices:
            to_group.entries_indices.append(entry_index)
    
    def get_entry_group(self, entry_index: int) -> WatchlistGroup:
        """Find which group contains this entry."""
        for group in self.get_all_groups():
            if entry_index in group.entries_indices:
                return group
        return self._default_group
    
    def update_entry_indices(self, old_to_new_map: Dict[int, int]) -> None:
        """Update all entry indices after watchlist reorder/delete."""
        for group in self.get_all_groups():
            new_indices = []
            for old_idx in group.entries_indices:
                if old_idx in old_to_new_map:
                    new_indices.append(old_to_new_map[old_idx])
            group.entries_indices = new_indices
    
    def save_groups(self) -> bool:
        """Save group configuration."""
        try:
            data = {
                "groups": [g.to_dict() for g in self._groups if g != self._default_group],
                "default_expanded": self._default_group.expanded
            }
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            log.info("WatchlistGroupManager: Saved %d groups", len(self._groups))
            return True
            
        except Exception as e:
            log.error("WatchlistGroupManager: Save failed: %s", e)
            return False
    
    def load_groups(self) -> bool:
        """Load group configuration."""
        try:
            if not os.path.exists(self._config_path):
                return True
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Clear existing custom groups
            self._groups.clear()
            
            # Load groups
            for group_data in data.get("groups", []):
                try:
                    group = WatchlistGroup.from_dict(group_data)
                    self._groups.append(group)
                except Exception as e:
                    log.warning("WatchlistGroupManager: Failed to load group: %s", e)
            
            # Restore default group state
            self._default_group.expanded = data.get("default_expanded", True)
            
            log.info("WatchlistGroupManager: Loaded %d groups", len(self._groups))
            return True
            
        except Exception as e:
            log.error("WatchlistGroupManager: Load failed: %s", e)
            return False
    
    @staticmethod
    def get_color_choices() -> List[tuple]:
        """Get list of available colors with names."""
        return [
            ("Kırmızı", GroupColor.RED.value),
            ("Yeşil", GroupColor.GREEN.value),
            ("Mavi", GroupColor.BLUE.value),
            ("Sarı", GroupColor.YELLOW.value),
            ("Mor", GroupColor.PURPLE.value),
            ("Turuncu", GroupColor.ORANGE.value),
            ("Turkuaz", GroupColor.CYAN.value),
            ("Pembe", GroupColor.PINK.value),
            ("Gri", GroupColor.GRAY.value),
            ("Beyaz", GroupColor.WHITE.value),
        ]


# Global instance
group_manager = WatchlistGroupManager()
