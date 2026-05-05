"""
advanced_filters.py — Advanced scanning filters and options.
Provides additional filtering capabilities for memory scanning.
"""
from typing import Optional, List, Callable, Any, Dict
from dataclasses import dataclass
from enum import Enum, auto

from utils.patterns import DataType
from utils.logger import log


class FilterType(Enum):
    """Types of advanced filters."""
    ALIGNMENT = "alignment"          # Memory alignment
    RANGE = "range"                  # Address range
    MODULE = "module"                # Specific module
    PROTECTION = "protection"        # Memory protection
    VALUE_RANGE = "value_range"      # Value range
    CHANGED_RATE = "changed_rate"    # Change frequency
    NEAR_POINTER = "near_pointer"     # Near pointer addresses


@dataclass
class ScanFilter:
    """Represents a scan filter configuration."""
    filter_type: FilterType
    enabled: bool = True
    params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


class AdvancedFilterManager:
    """
    Manages advanced filtering for memory scanning.
    """
    
    def __init__(self):
        self._filters: List[ScanFilter] = []
        self._enabled = True
    
    def add_filter(self, filter_config: ScanFilter) -> None:
        """Add a filter to the manager."""
        self._filters.append(filter_config)
    
    def remove_filter(self, index: int) -> bool:
        """Remove a filter by index."""
        if 0 <= index < len(self._filters):
            del self._filters[index]
            return True
        return False
    
    def clear_filters(self) -> None:
        """Clear all filters."""
        self._filters.clear()
    
    def get_filters(self) -> List[ScanFilter]:
        """Get all filters."""
        return self._filters.copy()
    
    def enable_all(self) -> None:
        """Enable all filters."""
        for f in self._filters:
            f.enabled = True
    
    def disable_all(self) -> None:
        """Disable all filters."""
        for f in self._filters:
            f.enabled = False
    
    def filter_addresses(self, addresses: List[int]) -> List[int]:
        """
        Apply all enabled filters to address list.
        
        Args:
            addresses: List of addresses to filter
        
        Returns:
            Filtered address list
        """
        result = addresses.copy()
        
        for filter_config in self._filters:
            if not filter_config.enabled:
                continue
            
            if filter_config.filter_type == FilterType.ALIGNMENT:
                result = self._apply_alignment_filter(result, filter_config.params)
            elif filter_config.filter_type == FilterType.RANGE:
                result = self._apply_range_filter(result, filter_config.params)
        
        return result
    
    def _apply_alignment_filter(self, addresses: List[int], params: Dict) -> List[int]:
        """Filter by memory alignment."""
        alignment = params.get("alignment", 4)
        return [addr for addr in addresses if addr % alignment == 0]
    
    def _apply_range_filter(self, addresses: List[int], params: Dict) -> List[int]:
        """Filter by address range."""
        min_addr = params.get("min", 0)
        max_addr = params.get("max", 0xFFFFFFFFFFFFFFFF)
        return [addr for addr in addresses if min_addr <= addr <= max_addr]
    
    def filter_results(self, 
                       results: List[tuple], 
                       dtype: DataType,
                       custom_filter: Optional[Callable[[Any], bool]] = None) -> List[tuple]:
        """
        Apply advanced filters to scan results.
        
        Args:
            results: List of (address, value) tuples
            dtype: Data type
            custom_filter: Optional custom filter function
        
        Returns:
            Filtered results
        """
        if not self._enabled:
            return results
        
        filtered = results
        
        for filter_config in self._filters:
            if not filter_config.enabled:
                continue
            
            if filter_config.filter_type == FilterType.VALUE_RANGE:
                filtered = self._apply_value_range_filter(filtered, filter_config.params, dtype)
            elif filter_config.filter_type == FilterType.CUSTOM and custom_filter:
                filtered = [r for r in filtered if custom_filter(r[1])]
        
        return filtered
    
    def _apply_value_range_filter(self, 
                                   results: List[tuple], 
                                   params: Dict, 
                                   dtype: DataType) -> List[tuple]:
        """Filter by value range."""
        min_val = params.get("min")
        max_val = params.get("max")
        
        if min_val is None and max_val is None:
            return results
        
        filtered = []
        for addr, val in results:
            try:
                if min_val is not None and val < min_val:
                    continue
                if max_val is not None and val > max_val:
                    continue
                filtered.append((addr, val))
            except TypeError:
                # Non-comparable type, skip filter
                filtered.append((addr, val))
        
        return filtered


class ScanOptimizer:
    """
    Optimizes scan performance with various strategies.
    """
    
    def __init__(self):
        self._chunk_size = 4096
        self._use_threading = True
        self._max_workers = 4
    
    def optimize_chunk_size(self, data_type: DataType, total_memory: int) -> int:
        """
        Calculate optimal chunk size based on data type and memory.
        
        Args:
            data_type: Type of data being scanned
            total_memory: Total memory size to scan
        
        Returns:
            Optimal chunk size in bytes
        """
        type_sizes = {
            DataType.INT8: 1,
            DataType.INT16: 2,
            DataType.INT32: 4,
            DataType.INT64: 8,
            DataType.FLOAT: 4,
            DataType.DOUBLE: 8,
        }
        
        element_size = type_sizes.get(dtype, 4)
        
        # Aim for chunks that fit ~1000 elements
        base_chunk = element_size * 1000
        
        # Adjust based on total memory
        if total_memory > 1_000_000_000:  # > 1GB
            return base_chunk * 4
        elif total_memory > 100_000_000:  # > 100MB
            return base_chunk * 2
        
        return base_chunk
    
    def should_use_threading(self, region_count: int) -> bool:
        """
        Determine if threading should be used based on region count.
        
        Args:
            region_count: Number of memory regions
        
        Returns:
            True if threading is beneficial
        """
        return region_count > 2 and self._use_threading
    
    def get_optimal_workers(self, region_count: int) -> int:
        """
        Get optimal number of worker threads.
        
        Args:
            region_count: Number of memory regions
        
        Returns:
            Optimal worker count
        """
        import os
        cpu_count = os.cpu_count() or 4
        return min(region_count, cpu_count, self._max_workers)


# Global instance
advanced_filters = AdvancedFilterManager()
scan_optimizer = ScanOptimizer()
