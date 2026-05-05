"""
memory_map.py — Memory region mapping and analysis.
Displays process memory layout with protection flags and details.
"""
import ctypes
from ctypes import wintypes
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum

from utils.logger import log


# MEMORY_BASIC_INFORMATION structure for VirtualQueryEx
class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    """Windows MEMORY_BASIC_INFORMATION structure."""
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),  # Windows 10+
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


class MemoryProtection(Enum):
    """Windows memory protection flags."""
    PAGE_NOACCESS = 0x01
    PAGE_READONLY = 0x02
    PAGE_READWRITE = 0x04
    PAGE_WRITECOPY = 0x08
    PAGE_EXECUTE = 0x10
    PAGE_EXECUTE_READ = 0x20
    PAGE_EXECUTE_READWRITE = 0x40
    PAGE_EXECUTE_WRITECOPY = 0x80
    PAGE_GUARD = 0x100
    PAGE_NOCACHE = 0x200
    PAGE_WRITECOMBINE = 0x400


class MemoryState(Enum):
    """Windows memory state flags."""
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    MEM_FREE = 0x10000


class MemoryType(Enum):
    """Windows memory type flags."""
    MEM_PRIVATE = 0x20000
    MEM_MAPPED = 0x40000
    MEM_IMAGE = 0x1000000


@dataclass
class MemoryRegion:
    """Represents a single memory region."""
    base_address: int
    region_size: int
    state: int
    protect: int
    type: int
    allocation_base: int = 0
    allocation_protect: int = 0
    
    @property
    def state_name(self) -> str:
        """Get human-readable state name."""
        states = {
            MemoryState.MEM_COMMIT.value: "Commit",
            MemoryState.MEM_RESERVE.value: "Reserve",
            MemoryState.MEM_FREE.value: "Free",
        }
        return states.get(self.state, f"Unknown(0x{self.state:X})")
    
    @property
    def type_name(self) -> str:
        """Get human-readable type name."""
        types = {
            MemoryType.MEM_PRIVATE.value: "Private",
            MemoryType.MEM_MAPPED.value: "Mapped",
            MemoryType.MEM_IMAGE.value: "Image",
        }
        return types.get(self.type, f"Unknown(0x{self.type:X})")
    
    @property
    def protection_name(self) -> str:
        """Get human-readable protection name."""
        if self.protect == 0:
            return "No Access"
        
        flags = []
        
        # Basic protection
        if self.protect & MemoryProtection.PAGE_NOACCESS.value:
            flags.append("NoAccess")
        if self.protect & MemoryProtection.PAGE_READONLY.value:
            flags.append("Read")
        if self.protect & MemoryProtection.PAGE_READWRITE.value:
            flags.append("ReadWrite")
        if self.protect & MemoryProtection.PAGE_WRITECOPY.value:
            flags.append("WriteCopy")
        if self.protect & MemoryProtection.PAGE_EXECUTE.value:
            flags.append("Execute")
        if self.protect & MemoryProtection.PAGE_EXECUTE_READ.value:
            flags.append("ExecuteRead")
        if self.protect & MemoryProtection.PAGE_EXECUTE_READWRITE.value:
            flags.append("ExecuteReadWrite")
        if self.protect & MemoryProtection.PAGE_EXECUTE_WRITECOPY.value:
            flags.append("ExecuteWriteCopy")
        
        # Additional flags
        if self.protect & MemoryProtection.PAGE_GUARD.value:
            flags.append("Guard")
        if self.protect & MemoryProtection.PAGE_NOCACHE.value:
            flags.append("NoCache")
        if self.protect & MemoryProtection.PAGE_WRITECOMBINE.value:
            flags.append("WriteCombine")
        
        return " | ".join(flags) if flags else f"0x{self.protect:X}"
    
    @property
    def is_readable(self) -> bool:
        """Check if region is readable."""
        if self.state != MemoryState.MEM_COMMIT.value:
            return False
        readable_flags = (
            MemoryProtection.PAGE_READONLY.value |
            MemoryProtection.PAGE_READWRITE.value |
            MemoryProtection.PAGE_EXECUTE_READ.value |
            MemoryProtection.PAGE_EXECUTE_READWRITE.value
        )
        return (self.protect & readable_flags) != 0
    
    @property
    def is_writable(self) -> bool:
        """Check if region is writable."""
        if self.state != MemoryState.MEM_COMMIT.value:
            return False
        writable_flags = (
            MemoryProtection.PAGE_READWRITE.value |
            MemoryProtection.PAGE_WRITECOPY.value |
            MemoryProtection.PAGE_EXECUTE_READWRITE.value |
            MemoryProtection.PAGE_EXECUTE_WRITECOPY.value
        )
        return (self.protect & writable_flags) != 0
    
    @property
    def is_executable(self) -> bool:
        """Check if region is executable."""
        if self.state != MemoryState.MEM_COMMIT.value:
            return False
        exec_flags = (
            MemoryProtection.PAGE_EXECUTE.value |
            MemoryProtection.PAGE_EXECUTE_READ.value |
            MemoryProtection.PAGE_EXECUTE_READWRITE.value |
            MemoryProtection.PAGE_EXECUTE_WRITECOPY.value
        )
        return (self.protect & exec_flags) != 0
    
    @property
    def end_address(self) -> int:
        """Get end address of region."""
        return self.base_address + self.region_size
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "base_address": f"0x{self.base_address:X}",
            "end_address": f"0x{self.end_address:X}",
            "size": self.region_size,
            "size_human": self.format_size(self.region_size),
            "state": self.state_name,
            "type": self.type_name,
            "protection": self.protection_name,
            "readable": self.is_readable,
            "writable": self.is_writable,
            "executable": self.is_executable,
        }
    
    @staticmethod
    def format_size(size: int) -> str:
        """Format size to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MemoryMap:
    """
    Memory mapping and analysis for a process.
    """
    
    def __init__(self, process_handle: int):
        """
        Initialize memory map.
        
        Args:
            process_handle: Windows process handle
        """
        self._handle = process_handle
        self._regions: List[MemoryRegion] = []
    
    def scan(self) -> List[MemoryRegion]:
        """
        Scan all memory regions in the process.
        
        Returns:
            List of MemoryRegion objects
        """
        self._regions = []
        
        if not self._handle:
            log.error("MemoryMap: No process handle")
            return []
        
        address = 0
        max_address = 0x7FFFFFFF if ctypes.sizeof(ctypes.c_void_p) == 4 else 0x7FFFFFFFFFFFFFFF
        
        while address < max_address:
            mbi = self._query_address(address)
            if not mbi:
                break
            
            # Ensure values are integers (not None)
            base_addr = mbi.BaseAddress or 0
            region_sz = mbi.RegionSize or 0
            
            if region_sz == 0:
                break  # Invalid region size, stop scanning
            
            region = MemoryRegion(
                base_address=base_addr,
                region_size=region_sz,
                state=mbi.State or 0,
                protect=mbi.Protect or 0,
                type=mbi.Type or 0,
                allocation_base=mbi.AllocationBase or 0,
                allocation_protect=mbi.AllocationProtect or 0
            )
            
            self._regions.append(region)
            
            # Move to next region
            next_address = base_addr + region_sz
            if next_address <= address:
                break  # Prevent infinite loop
            address = next_address
        
        log.info("MemoryMap: Scanned %d regions", len(self._regions))
        return self._regions
    
    def _query_address(self, address: int) -> Optional[MEMORY_BASIC_INFORMATION]:
        """Query memory information at given address."""
        mbi = MEMORY_BASIC_INFORMATION()
        
        kernel32 = ctypes.windll.kernel32
        kernel32.VirtualQueryEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.POINTER(MEMORY_BASIC_INFORMATION),
            ctypes.c_size_t
        ]
        kernel32.VirtualQueryEx.restype = ctypes.c_size_t
        
        result = kernel32.VirtualQueryEx(
            self._handle,
            ctypes.c_void_p(address),
            ctypes.byref(mbi),
            ctypes.sizeof(mbi)
        )
        
        if result == 0:
            return None
        
        return mbi
    
    def get_regions(self) -> List[MemoryRegion]:
        """Get all scanned regions."""
        return self._regions
    
    def get_readable_regions(self) -> List[MemoryRegion]:
        """Get only readable regions."""
        return [r for r in self._regions if r.is_readable]
    
    def get_writable_regions(self) -> List[MemoryRegion]:
        """Get only writable regions."""
        return [r for r in self._regions if r.is_writable]
    
    def get_executable_regions(self) -> List[MemoryRegion]:
        """Get only executable regions (code sections)."""
        return [r for r in self._regions if r.is_executable]
    
    def find_region(self, address: int) -> Optional[MemoryRegion]:
        """Find region containing given address."""
        for region in self._regions:
            if region.base_address <= address < region.end_address:
                return region
        return None
    
    def get_statistics(self) -> Dict[str, any]:
        """Get memory statistics."""
        if not self._regions:
            return {}
        
        total_size = sum(r.region_size for r in self._regions)
        committed_size = sum(r.region_size for r in self._regions 
                           if r.state == MemoryState.MEM_COMMIT.value)
        reserved_size = sum(r.region_size for r in self._regions 
                          if r.state == MemoryState.MEM_RESERVE.value)
        
        readable_count = len([r for r in self._regions if r.is_readable])
        writable_count = len([r for r in self._regions if r.is_writable])
        executable_count = len([r for r in self._regions if r.is_executable])
        
        return {
            "total_regions": len(self._regions),
            "total_size": total_size,
            "total_size_human": MemoryRegion.format_size(total_size),
            "committed_size": committed_size,
            "committed_size_human": MemoryRegion.format_size(committed_size),
            "reserved_size": reserved_size,
            "reserved_size_human": MemoryRegion.format_size(reserved_size),
            "readable_regions": readable_count,
            "writable_regions": writable_count,
            "executable_regions": executable_count,
        }
    
    def filter_regions(self, 
                       readable: Optional[bool] = None,
                       writable: Optional[bool] = None,
                       executable: Optional[bool] = None,
                       min_size: Optional[int] = None,
                       max_size: Optional[int] = None) -> List[MemoryRegion]:
        """
        Filter regions by criteria.
        
        Args:
            readable: Filter by readability
            writable: Filter by writability
            executable: Filter by executability
            min_size: Minimum region size
            max_size: Maximum region size
        
        Returns:
            Filtered list of regions
        """
        result = self._regions.copy()
        
        if readable is not None:
            result = [r for r in result if r.is_readable == readable]
        
        if writable is not None:
            result = [r for r in result if r.is_writable == writable]
        
        if executable is not None:
            result = [r for r in result if r.is_executable == executable]
        
        if min_size is not None:
            result = [r for r in result if r.region_size >= min_size]
        
        if max_size is not None:
            result = [r for r in result if r.region_size <= max_size]
        
        return result
    
    def export_to_json(self, filepath: str) -> bool:
        """Export memory map to JSON."""
        try:
            import json
            data = {
                "statistics": self.get_statistics(),
                "regions": [r.to_dict() for r in self._regions]
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            log.error("MemoryMap: Export failed: %s", e)
            return False


# Global instance (requires process handle to be useful)
memory_map_instance: Optional[MemoryMap] = None
