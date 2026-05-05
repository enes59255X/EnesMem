"""
compare_scanner.py — Compare/Diff scanning functionality.
Allows comparing memory values between two different times/states.
"""
from typing import Optional, List, Dict, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import struct
import time

from utils.patterns import DataType, ScanMode
from utils.logger import log


class CompareType(Enum):
    """Types of compare operations."""
    CHANGED = "changed"           # Value changed from snapshot
    UNCHANGED = "unchanged"       # Value unchanged from snapshot
    INCREASED = "increased"       # Value increased
    DECREASED = "decreased"       # Value decreased
    INCREASED_BY = "increased_by" # Increased by specific amount
    DECREASED_BY = "decreased_by" # Decreased by specific amount
    EQUAL = "equal"               # Equal to specific value
    NOT_EQUAL = "not_equal"       # Not equal to specific value


@dataclass
class MemorySnapshot:
    """Snapshot of memory values at a point in time."""
    timestamp: float
    values: Dict[int, any] = field(default_factory=dict)
    dtype: DataType = DataType.INT32
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "values": {f"0x{k:X}": v for k, v in self.values.items()},
            "dtype": self.dtype.value
        }


@dataclass
class CompareResult:
    """Result of a compare operation."""
    address: int
    old_value: any
    new_value: any
    change_type: str
    change_amount: Optional[float] = None


class CompareScanner:
    """
    Scanner for compare/diff operations.
    Tracks value changes over time and allows filtering.
    """
    
    def __init__(self, mem_io):
        """
        Initialize compare scanner.
        
        Args:
            mem_io: MemoryIO instance for reading memory
        """
        self._mem_io = mem_io
        self._snapshots: Dict[str, MemorySnapshot] = {}
        self._last_results: List[int] = []
    
    def take_snapshot(self, name: str, addresses: List[int], dtype: DataType = DataType.INT32) -> MemorySnapshot:
        """
        Take a snapshot of current values at given addresses.
        
        Args:
            name: Name for this snapshot
            addresses: List of addresses to snapshot
            dtype: Data type to read
        
        Returns:
            MemorySnapshot object
        """
        values = {}
        
        for addr in addresses:
            try:
                val = self._mem_io.read_value(addr, dtype)
                if val is not None:
                    values[addr] = val
            except Exception as e:
                log.debug("CompareScanner: Failed to read 0x%X: %s", addr, e)
        
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            values=values,
            dtype=dtype
        )
        
        self._snapshots[name] = snapshot
        log.info("CompareScanner: Snapshot '%s' created with %d values", name, len(values))
        return snapshot
    
    def get_snapshot(self, name: str) -> Optional[MemorySnapshot]:
        """Get a snapshot by name."""
        return self._snapshots.get(name)
    
    def delete_snapshot(self, name: str) -> bool:
        """Delete a snapshot."""
        if name in self._snapshots:
            del self._snapshots[name]
            return True
        return False
    
    def list_snapshots(self) -> List[str]:
        """List all snapshot names."""
        return list(self._snapshots.keys())
    
    def compare(self, 
                snapshot_name: str, 
                addresses: Optional[List[int]] = None,
                compare_type: CompareType = CompareType.CHANGED,
                compare_value: Optional[float] = None) -> List[CompareResult]:
        """
        Compare current values against a snapshot.
        
        Args:
            snapshot_name: Name of snapshot to compare against
            addresses: Optional list of addresses (uses snapshot addresses if None)
            compare_type: Type of comparison to perform
            compare_value: Optional value for EQUAL, NOT_EQUAL, INCREASED_BY, DECREASED_BY
        
        Returns:
            List of CompareResult objects
        """
        snapshot = self._snapshots.get(snapshot_name)
        if not snapshot:
            log.error("CompareScanner: Snapshot '%s' not found", snapshot_name)
            return []
        
        if addresses is None:
            addresses = list(snapshot.values.keys())
        
        results = []
        dtype = snapshot.dtype
        
        for addr in addresses:
            old_val = snapshot.values.get(addr)
            if old_val is None:
                continue
            
            try:
                new_val = self._mem_io.read_value(addr, dtype)
                if new_val is None:
                    continue
            except Exception:
                continue
            
            result = self._check_compare(old_val, new_val, compare_type, compare_value)
            if result:
                change_amount = None
                if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                    change_amount = float(new_val) - float(old_val)
                
                results.append(CompareResult(
                    address=addr,
                    old_value=old_val,
                    new_value=new_val,
                    change_type=compare_type.value,
                    change_amount=change_amount
                ))
        
        self._last_results = [r.address for r in results]
        log.info("CompareScanner: Compare '%s' found %d results", compare_type.value, len(results))
        return results
    
    def _check_compare(self, old_val: any, new_val: any, 
                       compare_type: CompareType, compare_value: Optional[float]) -> bool:
        """Check if values match the comparison criteria."""
        
        if compare_type == CompareType.CHANGED:
            return old_val != new_val
        
        elif compare_type == CompareType.UNCHANGED:
            return old_val == new_val
        
        elif compare_type == CompareType.INCREASED:
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                return new_val > old_val
            return False
        
        elif compare_type == CompareType.DECREASED:
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                return new_val < old_val
            return False
        
        elif compare_type == CompareType.INCREASED_BY:
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                diff = new_val - old_val
                return abs(diff - (compare_value or 0)) < 0.0001
            return False
        
        elif compare_type == CompareType.DECREASED_BY:
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                diff = old_val - new_val
                return abs(diff - (compare_value or 0)) < 0.0001
            return False
        
        elif compare_type == CompareType.EQUAL:
            return new_val == (compare_value or 0)
        
        elif compare_type == CompareType.NOT_EQUAL:
            return new_val != (compare_value or 0)
        
        return False
    
    def compare_with_previous(self, 
                              addresses: List[int], 
                              dtype: DataType = DataType.INT32,
                              compare_type: CompareType = CompareType.CHANGED) -> List[CompareResult]:
        """
        Quick compare using internal last values.
        Automatically takes a new snapshot and compares.
        
        Args:
            addresses: List of addresses to check
            dtype: Data type
            compare_type: Type of comparison
        
        Returns:
            List of CompareResult objects
        """
        # Take temporary snapshot
        temp_name = f"_temp_{time.time()}"
        self.take_snapshot(temp_name, addresses, dtype)
        
        # If we have a previous snapshot, compare against it
        if "_previous" in self._snapshots:
            results = self.compare("_previous", addresses, compare_type)
        else:
            results = []
        
        # Save this as previous for next time
        self._snapshots["_previous"] = self._snapshots[temp_name]
        del self._snapshots[temp_name]
        
        return results
    
    def find_changed_addresses(self, 
                                addresses: List[int], 
                                dtype: DataType = DataType.INT32,
                                interval_ms: int = 1000,
                                duration_ms: int = 5000,
                                callback: Optional[Callable[[List[CompareResult]], None]] = None) -> Dict[int, List[any]]:
        """
        Monitor addresses over time to find changing values.
        
        Args:
            addresses: List of addresses to monitor
            dtype: Data type
            interval_ms: Milliseconds between reads
            duration_ms: Total duration to monitor
            callback: Optional callback function called after each interval
        
        Returns:
            Dictionary mapping addresses to lists of values over time
        """
        changes: Dict[int, List[any]] = {addr: [] for addr in addresses}
        start_time = time.time()
        interval_sec = interval_ms / 1000.0
        
        while (time.time() - start_time) * 1000 < duration_ms:
            current_results = []
            
            for addr in addresses:
                try:
                    val = self._mem_io.read_value(addr, dtype)
                    if val is not None:
                        changes[addr].append(val)
                        
                        # Track if changed from previous
                        if len(changes[addr]) > 1 and changes[addr][-1] != changes[addr][-2]:
                            current_results.append(CompareResult(
                                address=addr,
                                old_value=changes[addr][-2],
                                new_value=val,
                                change_type="changed",
                                change_amount=None
                            ))
                except Exception as e:
                    log.debug("CompareScanner: Read error at 0x%X: %s", addr, e)
            
            if callback and current_results:
                callback(current_results)
            
            time.sleep(interval_sec)
        
        log.info("CompareScanner: Monitored %d addresses for %d ms", len(addresses), duration_ms)
        return changes
    
    def get_value_history(self, address: int, 
                          samples: int = 10, 
                          interval_ms: int = 100,
                          dtype: DataType = DataType.INT32) -> List[any]:
        """
        Get history of values for a single address.
        
        Args:
            address: Address to monitor
            samples: Number of samples to take
            interval_ms: Milliseconds between samples
            dtype: Data type
        
        Returns:
            List of values
        """
        values = []
        interval_sec = interval_ms / 1000.0
        
        for _ in range(samples):
            try:
                val = self._mem_io.read_value(address, dtype)
                if val is not None:
                    values.append(val)
            except Exception:
                pass
            time.sleep(interval_sec)
        
        return values
    
    def clear_snapshots(self) -> None:
        """Clear all snapshots."""
        self._snapshots.clear()
        self._last_results = []
        log.info("CompareScanner: All snapshots cleared")
    
    def export_results(self, results: List[CompareResult], filepath: str) -> bool:
        """Export compare results to JSON."""
        try:
            import json
            data = [{
                "address": f"0x{r.address:X}",
                "old_value": r.old_value,
                "new_value": r.new_value,
                "change_type": r.change_type,
                "change_amount": r.change_amount
            } for r in results]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            log.error("CompareScanner: Export failed: %s", e)
            return False


class DiffScanner(CompareScanner):
    """
    Extended scanner for diff-style comparisons.
    Provides additional methods for finding differences between two scans.
    """
    
    def diff_scan(self, 
                  first_results: List[int], 
                  second_results: List[int]) -> Tuple[List[int], List[int], List[int]]:
        """
        Find differences between two scan result sets.
        
        Args:
            first_results: First scan results (list of addresses)
            second_results: Second scan results (list of addresses)
        
        Returns:
            Tuple of (added, removed, common) addresses
        """
        first_set = set(first_results)
        second_set = set(second_results)
        
        added = list(second_set - first_set)
        removed = list(first_set - second_set)
        common = list(first_set & second_set)
        
        log.info("DiffScanner: Added=%d, Removed=%d, Common=%d", len(added), len(removed), len(common))
        return added, removed, common
    
    def filter_by_change_rate(self,
                              addresses: List[int],
                              dtype: DataType = DataType.INT32,
                              min_changes: int = 2,
                              samples: int = 10,
                              interval_ms: int = 100) -> List[int]:
        """
        Filter addresses by their change rate.
        Useful for finding values that change frequently (e.g., timers).
        
        Args:
            addresses: List of addresses to check
            dtype: Data type
            min_changes: Minimum number of changes required
            samples: Number of samples to take
            interval_ms: Milliseconds between samples
        
        Returns:
            List of addresses that changed at least min_changes times
        """
        changing_addresses = []
        interval_sec = interval_ms / 1000.0
        
        for addr in addresses:
            changes = 0
            prev_val = None
            
            for _ in range(samples):
                try:
                    val = self._mem_io.read_value(addr, dtype)
                    if val is not None:
                        if prev_val is not None and val != prev_val:
                            changes += 1
                        prev_val = val
                except Exception:
                    pass
                
                time.sleep(interval_sec)
            
            if changes >= min_changes:
                changing_addresses.append(addr)
        
        log.info("DiffScanner: Found %d frequently changing addresses (min %d changes)", 
                 len(changing_addresses), min_changes)
        return changing_addresses
