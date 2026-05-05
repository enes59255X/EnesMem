"""
scanner.py — Memory scan engine.
Supports First Scan, Next Scan, AOB scan, float tolerance, and all scan modes.

Performance design:
- First scan: bulk ReadProcessMemory per region → memoryview slice per address
- Next scan: re-reads only previous result addresses (fast path)
- AOB scan: Boyer-Moore-Horspool with wildcard mask
- Thread-safe via RLock
"""
import struct
import threading
import tempfile
import os
from dataclasses import dataclass
from typing import Callable, Optional

from core.memory_io import MemoryIO
from utils.converters import bytes_to_value, value_to_bytes, format_value
from utils.logger import log
from utils.patterns import (
    DataType, ScanMode, DATA_TYPE_SIZE, DATA_TYPE_STRUCT,
    RELATIVE_SCAN_MODES, VALUE_INPUT_MODES, NUMERIC_TYPES,
    FLOAT_TYPES, SCAN_CHUNK_SIZE,
)


@dataclass
class ScanResult:
    address:        int
    current_bytes:  bytes   # most-recently read bytes
    previous_bytes: bytes   # bytes from scan before this one

    def current_value(self, dtype: DataType):
        return bytes_to_value(self.current_bytes, dtype)

    def previous_value(self, dtype: DataType):
        return bytes_to_value(self.previous_bytes, dtype)


class Scanner:
    """
    Stateful scan engine.
    One Scanner instance per attached process.
    """

    def __init__(self, memory: MemoryIO) -> None:
        self._mem        = memory
        self._lock       = threading.RLock()
        self._results:   dict[int, ScanResult] = {}
        # UIV storage: (address, offset_in_file, size)
        self._uiv_index: list[tuple[int, int, int]] = []
        self._uiv_temp_path: Optional[str] = None
        self._scan_count: int  = 0
        self._dtype:     DataType = DataType.INT32
        self._cancelled: bool  = False

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def result_count(self) -> int:
        with self._lock:
            return len(self._results)

    @property
    def scan_count(self) -> int:
        return self._scan_count

    @property
    def dtype(self) -> DataType:
        return self._dtype

    def get_results(self) -> list[ScanResult]:
        with self._lock:
            return list(self._results.values())

    def get_result_at(self, index: int) -> Optional[ScanResult]:
        with self._lock:
            try:
                return list(self._results.values())[index]
            except IndexError:
                return None

    def get_results_slice(self, start: int, count: int) -> list[ScanResult]:
        """Returns a slice of results to avoid memory pressure on UI."""
        with self._lock:
            vals = list(self._results.values())
            return vals[start : start + count]

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        with self._lock:
            self._results.clear()
            self._uiv_index.clear()
            self._cleanup_uiv_file()
            self._scan_count = 0
            self._cancelled  = False
        log.info("Scanner reset")

    def _cleanup_uiv_file(self) -> None:
        if self._uiv_temp_path and os.path.exists(self._uiv_temp_path):
            try:
                os.remove(self._uiv_temp_path)
            except Exception as e:
                log.warning("Failed to remove UIV temp file: %s", e)
        self._uiv_temp_path = None

    # ── First Scan ────────────────────────────────────────────────────────────

    def first_scan(
        self,
        dtype:       DataType,
        mode:        ScanMode,
        value=None,
        tolerance:   float = 0.0,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> int:
        """
        Perform an initial scan across all memory regions.

        Args:
            dtype:       Target data type.
            mode:        Scan mode.
            value:       Target value (required for VALUE_INPUT_MODES).
            tolerance:   Delta for FLOAT_TOLERANCE mode.
            progress_cb: Called with 0-100 progress.

        Returns:
            Number of matching addresses found.
        """
        # AOB scan has its own fast path
        if mode == ScanMode.AOB:
            if isinstance(value, tuple) and len(value) == 2:
                pattern, mask = value
                return self._first_scan_aob(pattern, mask, progress_cb)
            elif isinstance(value, (bytes, bytearray)):
                return self._first_scan_aob(value, "", progress_cb)

        self.reset()
        self._dtype     = dtype
        self._cancelled = False

        target_bytes: Optional[bytes] = None
        if mode in VALUE_INPUT_MODES and value is not None and mode != ScanMode.FLOAT_TOLERANCE:
            target_bytes = value_to_bytes(value, dtype)
            if target_bytes is None:
                log.error("first_scan: cannot pack value %r as %s", value, dtype)
                return 0

        value_size = DATA_TYPE_SIZE.get(dtype)
        if value_size is None:
            value_size = len(target_bytes) if target_bytes else 4

        regions     = self._mem.get_regions(writable_only=False)
        total_bytes = sum(r.size for r in regions)
        scanned     = 0
        last_pct    = -1
        new_results: dict[int, ScanResult] = {}

        if mode == ScanMode.UNKNOWN:
            log.info("First scan (UIV): dtype=%s regions=%d total=%.1f MB", dtype.name, len(regions), total_bytes / 1048576)
            
            # Create temporary file for UIV storage
            fd, temp_path = tempfile.mkstemp(suffix=".uiv", prefix="enesmem_")
            self._uiv_temp_path = temp_path
            
            new_index = []
            current_offset = 0
            
            try:
                with os.fdopen(fd, "wb") as f:
                    for region in regions:
                        if self._cancelled:
                            log.info("First scan cancelled — partial UIV")
                            break
                        for chunk_base, chunk_bytes in self._mem.read_region_chunked(region):
                            if self._cancelled: break
                            
                            f.write(chunk_bytes)
                            new_index.append((chunk_base, current_offset, len(chunk_bytes)))
                            
                            current_offset += len(chunk_bytes)
                            scanned += len(chunk_bytes)
                            
                            # Safe scan throttling
                            from utils.settings import settings
                            if settings.safe_scan:
                                import time
                                time.sleep(0.005) # 5ms delay per chunk

                            if progress_cb:
                                pct = int(scanned * 100 / max(total_bytes, 1))
                                if pct > last_pct:
                                    progress_cb(pct)
                                    last_pct = pct
                
                with self._lock:
                    self._uiv_index = new_index
                    self._scan_count = 1
                
                log.info("First scan (UIV) done: %d chunks saved to disk (%s)", len(new_index), temp_path)
                if progress_cb: progress_cb(100)
                # Potential result count (aligned)
                return sum(size for _, _, size in new_index) // (value_size or 4)
                
            except Exception as e:
                log.error("First scan (UIV) failed during disk write: %s", e)
                self._cleanup_uiv_file()
                return 0

        log.info(
            "First scan: dtype=%s mode=%s value=%r  regions=%d  total=%.1f MB",
            dtype.name, mode.name, value, len(regions), total_bytes / 1048576,
        )

        for region in regions:
            if self._cancelled:
                log.info("First scan cancelled — partial: %d", len(new_results))
                break

            for chunk_base, chunk_bytes in self._mem.read_region_chunked(region):
                if self._cancelled:
                    break

                chunk_len  = len(chunk_bytes)
                stride     = value_size

                # --- FAST PATH: EXACT MATCH ---
                if mode == ScanMode.EXACT and target_bytes is not None:
                    idx = 0
                    while True:
                        idx = chunk_bytes.find(target_bytes, idx)
                        if idx == -1:
                            break
                        
                        # Check memory alignment for numeric types
                        aligned = True
                        if dtype not in (DataType.STRING, DataType.STRING16, DataType.BYTES):
                            if idx % stride != 0:
                                aligned = False
                        
                        if aligned:
                            addr = chunk_base + idx
                            new_results[addr] = ScanResult(
                                address=addr,
                                current_bytes=target_bytes,
                                previous_bytes=target_bytes,
                            )
                        
                        idx += 1
                # --- SLOW PATH: OTHER MODES ---
                else:
                    chunk_view = memoryview(chunk_bytes)
                    i = 0
                    while i + stride <= chunk_len:
                        candidate = bytes(chunk_view[i: i + stride])

                        if self._matches_first(candidate, target_bytes, dtype, mode, value, tolerance):
                            addr = chunk_base + i
                            new_results[addr] = ScanResult(
                                address=addr,
                                current_bytes=candidate,
                                previous_bytes=candidate,
                            )

                        i += 1 if dtype in (DataType.STRING, DataType.STRING16, DataType.BYTES) else stride

                scanned += len(chunk_bytes)

                # Safe scan throttling
                from utils.settings import settings
                if settings.safe_scan:
                    import time
                    time.sleep(0.005) # 5ms delay per chunk

                if progress_cb:
                    # Throttle progress updates to avoid flooding the UI thread
                    pct = int(scanned * 100 / max(total_bytes, 1))
                    if pct > last_pct:
                        progress_cb(pct)
                        last_pct = pct

        with self._lock:
            self._results    = new_results
            self._scan_count = 1

        log.info("First scan done: %d results", len(new_results))
        if progress_cb:
            progress_cb(100)
        return len(new_results)

    # ── AOB Scan ──────────────────────────────────────────────────────────────

    def _first_scan_aob(
        self,
        pattern:     bytes,
        mask:        str = "",
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> int:
        """
        Scan for a byte pattern with optional wildcard mask.
        mask: string of 'x' (match) and '?' (wildcard), same length as pattern.
        If mask is empty, all bytes must match exactly.
        """
        self.reset()
        self._dtype     = DataType.BYTES
        self._cancelled = False

        if not mask:
            mask = "x" * len(pattern)

        pat_len     = len(pattern)
        regions     = self._mem.get_regions(writable_only=False)
        total_bytes = sum(r.size for r in regions)
        scanned     = 0
        last_pct    = -1
        new_results: dict[int, ScanResult] = {}

        log.info(
            "AOB scan: pattern=%s mask=%s  regions=%d  total=%.1f MB",
            pattern.hex(' '), mask, len(regions), total_bytes / 1048576,
        )

        for region in regions:
            if self._cancelled:
                break

            for chunk_base, chunk_bytes in self._mem.read_region_chunked(region):
                if self._cancelled:
                    break

                mv  = memoryview(chunk_bytes)
                cl  = len(chunk_bytes)

                for i in range(cl - pat_len + 1):
                    match = True
                    for j in range(pat_len):
                        if mask[j] == 'x' and mv[i + j] != pattern[j]:
                            match = False
                            break
                    if match:
                        addr = chunk_base + i
                        candidate = bytes(mv[i: i + pat_len])
                        new_results[addr] = ScanResult(
                            address=addr,
                            current_bytes=candidate,
                            previous_bytes=candidate,
                        )

                scanned += cl
                
                # Safe scan throttling
                from utils.settings import settings
                if settings.safe_scan:
                    import time
                    time.sleep(0.005) # 5ms delay per chunk

                if progress_cb:
                    pct = int(scanned * 100 / max(total_bytes, 1))
                    if pct > last_pct:
                        progress_cb(pct)
                        last_pct = pct

        with self._lock:
            self._results    = new_results
            self._scan_count = 1

        log.info("AOB scan done: %d results", len(new_results))
        if progress_cb:
            progress_cb(100)
        return len(new_results)

    # ── Next Scan ─────────────────────────────────────────────────────────────

    def next_scan(
        self,
        mode:        ScanMode,
        value=None,
        tolerance:   float = 0.0,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> int:
        if self._scan_count == 0:
            log.warning("next_scan called before first_scan")
            return 0

        self._cancelled = False

        target_bytes: Optional[bytes] = None
        if mode in VALUE_INPUT_MODES and value is not None and mode != ScanMode.FLOAT_TOLERANCE:
            target_bytes = value_to_bytes(value, self._dtype)

        value_size = DATA_TYPE_SIZE.get(self._dtype)
        if value_size is None:
            value_size = len(target_bytes) if target_bytes else 4

        kept: dict[int, ScanResult] = {}

        if self._uiv_index and self._uiv_temp_path:
            # First next_scan after an UNKNOWN first scan
            total_bytes = sum(size for _, _, size in self._uiv_index)
            scanned = 0
            last_pct = -1
            log.info("Next scan (from UIV disk): mode=%s value=%r", mode.name, value)
            
            try:
                with open(self._uiv_temp_path, "rb") as f:
                    for chunk_base, offset, chunk_len in self._uiv_index:
                        if self._cancelled:
                            break
                        
                        # Read old data from disk
                        f.seek(offset)
                        old_chunk_bytes = f.read(chunk_len)
                        
                        # Read current live memory
                        new_chunk_bytes = self._mem.read_bytes(chunk_base, chunk_len)
                        if new_chunk_bytes is None:
                            scanned += chunk_len
                            continue
                        
                        old_view = memoryview(old_chunk_bytes)
                        new_view = memoryview(new_chunk_bytes)
                        stride = value_size
                        i = 0
                        while i + stride <= chunk_len:
                            old_cand = bytes(old_view[i:i+stride])
                            new_cand = bytes(new_view[i:i+stride])
                            
                            if self._matches_next(
                                new_cand, old_cand, target_bytes, self._dtype, mode, value, tolerance
                            ):
                                addr = chunk_base + i
                                kept[addr] = ScanResult(
                                    address=addr,
                                    current_bytes=new_cand,
                                    previous_bytes=old_cand,
                                )
                            i += 1 if self._dtype in (DataType.STRING, DataType.BYTES) else stride

                        scanned += chunk_len
                        if progress_cb:
                            pct = int(scanned * 100 / max(total_bytes, 1))
                            if pct > last_pct:
                                progress_cb(pct)
                                last_pct = pct
                
                with self._lock:
                    self._results = kept
                    self._uiv_index.clear()
                    self._cleanup_uiv_file() # We now have concrete results in RAM
                    self._scan_count += 1
                    
            except Exception as e:
                log.error("Next scan (UIV) failed during disk read: %s", e)
                return 0
                
        else:
            with self._lock:
                prev_results = dict(self._results)

            total = len(prev_results)
            done  = 0
            last_pct = -1
            log.info("Next scan: mode=%s value=%r  candidates=%d", mode.name, value, total)

            ptr_mask = (1 << (8 * getattr(self._mem, '_ptr_size', 8))) - 1
            
            for addr, prev in prev_results.items():
                if self._cancelled:
                    break

                # Sanitization: Ensure address is unsigned
                addr = addr & ptr_mask
                
                new_bytes = self._mem.read_bytes(addr, value_size)
                if new_bytes is None:
                    done += 1
                    log.debug("Discarding 0x%X: read failed", addr)
                    continue

                if self._matches_next(
                    new_bytes, prev.current_bytes, target_bytes,
                    self._dtype, mode, value, tolerance,
                ):
                    kept[addr] = ScanResult(
                        address=addr,
                        current_bytes=new_bytes,
                        previous_bytes=prev.current_bytes,
                    )

                done += 1
                if progress_cb and done % 500 == 0:
                    pct = int(done * 100 / max(total, 1))
                    if pct > last_pct:
                        progress_cb(pct)
                        last_pct = pct

            with self._lock:
                self._results    = kept
                self._scan_count += 1

        log.info("Next scan done: %d results remaining", len(kept))
        if progress_cb:
            progress_cb(100)
        return len(kept)

    # ── Live value refresh ────────────────────────────────────────────────────

    def refresh_values(self, max_results: int = 2000) -> None:
        value_size = DATA_TYPE_SIZE.get(self._dtype) or 4
        with self._lock:
            addrs = list(self._results.keys())[:max_results]

        for addr in addrs:
            new_bytes = self._mem.read_bytes(addr, value_size)
            if new_bytes is not None:
                with self._lock:
                    if addr in self._results:
                        res = self._results[addr]
                        res.previous_bytes = res.current_bytes
                        res.current_bytes = new_bytes

    # ── Comparison helpers ────────────────────────────────────────────────────

    @staticmethod
    def _unpack(raw: bytes, dtype: DataType):
        fmt = DATA_TYPE_STRUCT.get(dtype)
        if fmt and len(raw) >= struct.calcsize(fmt):
            return struct.unpack_from(fmt, raw)[0]
        return None

    def _matches_first(
        self,
        candidate:    bytes,
        target_bytes: Optional[bytes],
        dtype:        DataType,
        mode:         ScanMode,
        value,
        tolerance:    float = 0.0,
    ) -> bool:
        if mode == ScanMode.UNKNOWN:
            return True

        if mode == ScanMode.EXACT:
            return candidate == target_bytes

        if mode == ScanMode.FLOAT_TOLERANCE and dtype in FLOAT_TYPES:
            cval = self._unpack(candidate, dtype)
            if cval is None or value is None:
                return False
            return abs(cval - value) <= tolerance

        if dtype in NUMERIC_TYPES:
            cval = self._unpack(candidate, dtype)
            if cval is None:
                return False
            if mode == ScanMode.BIGGER:
                return cval > value
            if mode == ScanMode.SMALLER:
                return cval < value
            if mode == ScanMode.BETWEEN and isinstance(value, (list, tuple)) and len(value) == 2:
                return value[0] <= cval <= value[1]

        return False

    def _matches_next(
        self,
        new_bytes:    bytes,
        old_bytes:    bytes,
        target_bytes: Optional[bytes],
        dtype:        DataType,
        mode:         ScanMode,
        value,
        tolerance:    float = 0.0,
    ) -> bool:
        if mode == ScanMode.EXACT:
            return new_bytes == target_bytes

        if mode == ScanMode.UNCHANGED:
            return new_bytes == old_bytes

        if mode == ScanMode.CHANGED:
            return new_bytes != old_bytes

        if mode == ScanMode.FLOAT_TOLERANCE and dtype in FLOAT_TYPES:
            nval = self._unpack(new_bytes, dtype)
            if nval is None or value is None:
                return False
            return abs(nval - value) <= tolerance

        if dtype in NUMERIC_TYPES:
            nval = self._unpack(new_bytes, dtype)
            oval = self._unpack(old_bytes, dtype)
            if nval is None or oval is None:
                return False

            if mode == ScanMode.BIGGER:
                return nval > value
            if mode == ScanMode.SMALLER:
                return nval < value
            if mode == ScanMode.INCREASED:
                return nval > oval
            if mode == ScanMode.DECREASED:
                return nval < oval
            if mode == ScanMode.INCREASED_BY:
                return (nval - oval) == value
            if mode == ScanMode.DECREASED_BY:
                return (oval - nval) == value
            if mode == ScanMode.UNKNOWN:
                return True
            if mode == ScanMode.BETWEEN and isinstance(value, (list, tuple)) and len(value) == 2:
                return value[0] <= nval <= value[1]

        return False
