"""
aob_scanner.py — Enhanced Array of Bytes scanning with pattern generation.
Extends the basic scanner with user-friendly wildcard patterns and AOB utilities.
"""
import re
from typing import Optional, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from core.memory_io import MemoryIO
from utils.logger import log


class WildcardType(Enum):
    """Types of wildcards supported."""
    ANY_BYTE = "?"       # Matches any single byte
    ANY_SEQUENCE = "*"   # Matches 0-N bytes (not implemented in basic scan)
    SKIP_BYTE = "x"      # Skip/don't care (for mask-based)


@dataclass
class AOBPattern:
    """Represents a parsed AOB pattern with wildcards."""
    raw_pattern: str
    bytes_pattern: bytes
    mask: str  # 'x' = match, '?' = wildcard
    description: str = ""
    
    def __post_init__(self):
        """Validate pattern after creation."""
        if len(self.bytes_pattern) != len(self.mask):
            raise ValueError(f"Pattern length ({len(self.bytes_pattern)}) != mask length ({len(self.mask)})")
    
    @property
    def length(self) -> int:
        return len(self.bytes_pattern)
    
    def to_display_string(self) -> str:
        """Convert to human-readable format."""
        parts = []
        for i, (b, m) in enumerate(zip(self.bytes_pattern, self.mask)):
            if m == '?':
                parts.append("??")
            else:
                parts.append(f"{b:02X}")
        return " ".join(parts)


def parse_aob_pattern(pattern_str: str) -> AOBPattern:
    """
    Parse an AOB pattern string with wildcards.
    
    Supported formats:
        - "FF 00 A1" - exact bytes
        - "FF ? A1" - wildcard at position 1
        - "FF ?? A1" - same as "?"
        - "FF * A1" - variable length wildcard (not implemented yet)
        - "0xFF 0x00 0xA1" - with 0x prefix
    
    Args:
        pattern_str: Space-separated hex bytes with optional wildcards
    
    Returns:
        AOBPattern object ready for scanning
    
    Raises:
        ValueError: If pattern is invalid
    """
    pattern_str = pattern_str.strip()
    if not pattern_str:
        raise ValueError("Empty pattern")
    
    # Normalize separators
    pattern_str = pattern_str.replace(",", " ")
    
    bytes_list = []
    mask_list = []
    
    for token in pattern_str.split():
        token = token.strip()
        if not token:
            continue
        
        # Check for wildcard
        if token in ['?', '??', '*', '**']:
            bytes_list.append(0x00)  # Placeholder byte
            mask_list.append('?')
        elif token.lower().startswith('0x'):
            # Hex with prefix
            try:
                byte_val = int(token, 16)
                if not 0 <= byte_val <= 255:
                    raise ValueError(f"Byte value out of range: {token}")
                bytes_list.append(byte_val)
                mask_list.append('x')
            except ValueError as e:
                raise ValueError(f"Invalid hex byte: {token}") from e
        else:
            # Hex without prefix
            try:
                if len(token) != 2:
                    raise ValueError(f"Byte must be 2 hex chars: {token}")
                byte_val = int(token, 16)
                bytes_list.append(byte_val)
                mask_list.append('x')
            except ValueError as e:
                raise ValueError(f"Invalid hex byte: {token}") from e
    
    if not bytes_list:
        raise ValueError("No valid bytes in pattern")
    
    return AOBPattern(
        raw_pattern=pattern_str,
        bytes_pattern=bytes(bytes_list),
        mask=''.join(mask_list)
    )


def generate_aob_pattern(
    data: bytes,
    tolerance: float = 0.0,
    min_length: int = 8,
    max_wildcards: int = 4
) -> AOBPattern:
    """
    Generate an AOB pattern from raw bytes with optional tolerance.
    
    This creates a pattern that will match similar memory regions.
    
    Args:
        data: Raw bytes to create pattern from
        tolerance: 0.0-1.0, percentage of bytes to wildcard (for fuzzy matching)
        min_length: Minimum pattern length
        max_wildcards: Maximum number of wildcards to insert
    
    Returns:
        AOBPattern ready for scanning
    """
    if len(data) < min_length:
        raise ValueError(f"Data too short for pattern (need {min_length}, got {len(data)})")
    
    # For now, use the full data as exact pattern
    # TODO: Implement smart pattern generation with:
    # - Identifying static vs dynamic bytes
    # - Common immediate values vs addresses
    # - Architecture-specific patterns (x86 vs x64)
    
    if tolerance > 0:
        # Insert wildcards based on tolerance
        import random
        mask = list('x' * len(data))
        num_wildcards = min(int(len(data) * tolerance), max_wildcards)
        
        # Don't wildcard first and last bytes (important for anchoring)
        wildcard_positions = random.sample(range(1, len(data) - 1), num_wildcards)
        for pos in wildcard_positions:
            mask[pos] = '?'
        
        return AOBPattern(
            raw_pattern=' '.join(f'{b:02X}' for b in data),
            bytes_pattern=data,
            mask=''.join(mask)
        )
    else:
        # Exact pattern
        return AOBPattern(
            raw_pattern=' '.join(f'{b:02X}' for b in data),
            bytes_pattern=data,
            mask='x' * len(data)
        )


def generate_pattern_from_address(
    mem: MemoryIO,
    address: int,
    length: int = 16,
    pointer_tolerance: bool = True
) -> Optional[AOBPattern]:
    """
    Generate an AOB pattern by reading memory at an address.
    
    Smart pattern generation that:
    - Detects pointers (addresses) and wildcard them
    - Keeps instruction bytes exact
    - Identifies common immediate values
    
    Args:
        mem: MemoryIO instance
        address: Address to read from
        length: Number of bytes to read
        pointer_tolerance: If True, detect and wildcard likely pointers
    
    Returns:
        AOBPattern or None if read failed
    """
    data = mem.read_bytes(address, length)
    if not data or len(data) < 8:
        return None
    
    mask = ['x'] * len(data)
    
    if pointer_tolerance:
        # Detect likely pointers (8-byte aligned values that look like addresses)
        # This is a heuristic - real pointers tend to be in certain ranges
        for i in range(0, len(data) - 7, 8):
            try:
                import struct
                val = struct.unpack('<Q', data[i:i+8])[0]
                # Heuristic: if value looks like a user-mode address
                if 0x10000 < val < 0x7FFFFFFF0000:
                    # Wildcard this likely pointer
                    for j in range(8):
                        if i + j < len(mask):
                            mask[i + j] = '?'
            except:
                pass
    
    return AOBPattern(
        raw_pattern=' '.join(f'{b:02X}' for b in data),
        bytes_pattern=data,
        mask=''.join(mask),
        description=f"Pattern @ 0x{address:X}"
    )


def aob_pattern_to_regex(pattern: AOBPattern) -> Optional[bytes]:
    """
    Convert AOB pattern to regex for searching.
    This is an alternative to Boyer-Moore for complex patterns.
    
    Args:
        pattern: AOBPattern to convert
    
    Returns:
        Regex pattern as bytes (for use with re.compile)
    """
    regex_parts = []
    for byte, mask_char in zip(pattern.bytes_pattern, pattern.mask):
        if mask_char == '?':
            regex_parts.append(b'.')  # Any byte
        else:
            regex_parts.append(bytes([byte]))
    
    return b''.join(regex_parts)


class AOBPatternLibrary:
    """
    Library of saved AOB patterns for common use cases.
    """
    
    COMMON_PATTERNS = {
        "unity_health_float": AOBPattern(
            "F3 0F 11 ?? ?? ?? ?? ?? F3 0F 10",
            b'\xf3\x0f\x11\x00\x00\x00\x00\x00\xf3\x0f\x10',
            "xxx?????xxx",
            "Unity Engine: Common health float write pattern"
        ),
        "unreal_engine_4": AOBPattern(
            "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 ?? 48 8B 40",
            b'\x48\x8b\x05\x00\x00\x00\x00\x48\x85\xc0\x74\x00\x48\x8b\x40',
            "xxx????xxxx?xxx",
            "Unreal Engine 4: Common pointer pattern"
        ),
        "x64_function_start": AOBPattern(
            "55 48 89 E5",
            b'\x55\x48\x89\xe5',
            "xxxx",
            "x64: push rbp; mov rbp, rsp (function prologue)"
        ),
    }
    
    def __init__(self, custom_patterns: Optional[dict] = None):
        self._patterns = dict(self.COMMON_PATTERNS)
        if custom_patterns:
            self._patterns.update(custom_patterns)
    
    def get_pattern(self, name: str) -> Optional[AOBPattern]:
        """Get a pattern by name."""
        return self._patterns.get(name)
    
    def add_pattern(self, name: str, pattern: AOBPattern) -> None:
        """Add a custom pattern."""
        self._patterns[name] = pattern
    
    def list_patterns(self) -> List[Tuple[str, str]]:
        """List all available patterns with descriptions."""
        return [(name, pat.description) for name, pat in self._patterns.items()]


class AOBToleranceScanner:
    """
    Scanner with tolerance/fuzzy matching for AOB patterns.
    Finds patterns that are "close enough" to the target.
    """
    
    def __init__(self, mem: MemoryIO):
        self._mem = mem
    
    def scan_with_tolerance(
        self,
        pattern: AOBPattern,
        tolerance_percent: float = 10.0,
        progress_cb: Optional[callable] = None
    ) -> List[int]:
        """
        Scan for patterns with tolerance for byte mismatches.
        
        Args:
            pattern: Target AOB pattern
            tolerance_percent: Percentage of bytes allowed to differ (0-100)
            progress_cb: Optional progress callback (percent)
        
        Returns:
            List of matching addresses
        """
        results = []
        pat_len = pattern.length
        
        # Calculate max allowed mismatches
        fixed_positions = pattern.mask.count('x')
        max_mismatches = int(fixed_positions * tolerance_percent / 100)
        
        if max_mismatches < 0:
            max_mismatches = 0
        
        regions = self._mem.get_regions(writable_only=False)
        total_bytes = sum(r.size for r in regions)
        scanned = 0
        
        for region in regions:
            for chunk_base, chunk_bytes in self._mem.read_region_chunked(region):
                chunk_len = len(chunk_bytes)
                
                # Scan through chunk
                for i in range(chunk_len - pat_len + 1):
                    mismatches = 0
                    match = True
                    
                    for j, mask_char in enumerate(pattern.mask):
                        if mask_char == 'x':  # Must match
                            if chunk_bytes[i + j] != pattern.bytes_pattern[j]:
                                mismatches += 1
                                if mismatches > max_mismatches:
                                    match = False
                                    break
                    
                    if match:
                        results.append(chunk_base + i)
                
                scanned += chunk_len
        
        if progress_cb:
            progress_cb(100)
        
        return results


# Convenience function for direct AOB scanning
def scan_aob_simple(
    mem: MemoryIO,
    pattern_str: str,
    progress_cb: Optional[callable] = None
) -> List[int]:
    """
    Simple AOB scan with string pattern.
    
    Args:
        mem: MemoryIO instance
        pattern_str: AOB pattern string (e.g., "FF 00 ?? A1")
        progress_cb: Optional progress callback
    
    Returns:
        List of matching addresses
    """
    try:
        pattern = parse_aob_pattern(pattern_str)
    except ValueError as e:
        log.error("AOB parse error: %s", e)
        return []
    
    # Use the scanner's built-in AOB method
    from core.scanner import Scanner
    scanner = Scanner(mem)
    
    count = scanner.first_scan(
        dtype=None,  # Not used for AOB
        mode=None,   # Not used for AOB
        value=(pattern.bytes_pattern, pattern.mask),
        progress_cb=progress_cb
    )
    
    results = []
    for res in scanner.get_results_slice(0, count):
        results.append(res.address)
    
    return results
