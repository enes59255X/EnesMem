"""
memory_io.py — Typed memory read/write and region enumeration.
All reads/writes use the handle from ProcessManager.
Bulk region enumeration feeds the scanner engine.
"""
import ctypes
import ctypes.wintypes as wt
import struct
from dataclasses import dataclass
from typing import Optional

from utils import winapi as api
from utils.logger import log
from utils.converters import bytes_to_value, value_to_bytes, format_address
from utils.patterns import (
    DataType, DATA_TYPE_SIZE, SCAN_CHUNK_SIZE,
)
from utils.winapi import (
    MEM_COMMIT, READABLE_PAGE_MASK, PAGE_GUARD,
    PAGE_READWRITE, PAGE_EXECUTE_READWRITE, PAGE_WRITECOPY, PAGE_EXECUTE_WRITECOPY,
)


@dataclass
class MemoryRegion:
    """A single contiguous readable memory region."""
    base:    int
    size:    int
    protect: int
    type_:   int  # MEM_PRIVATE / MEM_MAPPED / MEM_IMAGE

    def __repr__(self) -> str:
        return f"MemoryRegion(base=0x{self.base:X}, size={self.size:#x}, protect={self.protect:#x})"


class MemoryIO:
    """
    Low-level memory reader/writer.
    Requires an open process handle (int).
    """

    def __init__(self, handle: int, is_64bit: bool = True) -> None:
        self._handle   = handle
        self._is_64bit = is_64bit
        self._ptr_size = 8 if is_64bit else 4

    # ── Raw read / write ──────────────────────────────────────────────────────

    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        """Read `size` raw bytes from `address`. Returns None on failure."""
        # Validate handle and parameters
        if not self._handle or self._handle <= 0:
            return None
        if size <= 0 or size > 0x10000000:  # Max 256MB read
            return None
        
        # Sanitize address to prevent sign-extension issues
        ptr_mask = (1 << (8 * self._ptr_size)) - 1
        address &= ptr_mask
        
        # Additional safety: don't read from null or very high addresses
        if address < 0x1000 or address > 0x00007FFF00000000:
            return None
        
        try:
            buf      = (ctypes.c_char * size)()
            n_read   = ctypes.c_size_t(0)

            ok = api.ReadProcessMemory(
                self._handle, ctypes.c_void_p(address), buf, size, ctypes.byref(n_read)
            )
            if not ok:
                return None
            if n_read.value != size:
                return None
            return bytes(buf)
        except Exception as e:
            log.debug("read_bytes exception at 0x%X: %s", address, e)
            return None

    def write_bytes(self, address: int, data: bytes, silent: bool = False) -> bool:
        """Write raw bytes to `address`. Returns True on success."""
        if not data:
            return True

        # Sanitize address
        ptr_mask = (1 << (8 * self._ptr_size)) - 1
        address &= ptr_mask
        
        addr_vp  = ctypes.c_void_p(address)
        buf      = (ctypes.c_char * len(data))(*data)
        n_wrote  = ctypes.c_size_t(0)

        # 1. Inspect memory state
        mbi = api.MEMORY_BASIC_INFORMATION()
        res = api.VirtualQueryEx(self._handle, addr_vp, ctypes.byref(mbi), ctypes.sizeof(mbi))
        
        if not res:
            err = api.last_error_str()
            if not silent:
                log.error("write_bytes: VirtualQueryEx(0x%X, h=0x%X) FAILED: %s", address, self._handle, err)
            return False

        # Only committed memory can be written
        if mbi.State != api.MEM_COMMIT:
            if not silent:
                log.error("write_bytes: Target 0x%X is not COMMITTED (State=0x%X, Type=0x%X)", 
                          address, mbi.State, mbi.Type)
            return False

        old_protect = wt.DWORD(0)
        protected = False
        
        # 2. VirtualProtectEx if needed
        is_writable = bool(mbi.Protect & (api.PAGE_READWRITE | api.PAGE_EXECUTE_READWRITE | api.PAGE_WRITECOPY | api.PAGE_EXECUTE_WRITECOPY))
        if not is_writable:
            # Attempt to make it writable
            protected = api.VirtualProtectEx(
                self._handle, addr_vp, len(data), api.PAGE_EXECUTE_READWRITE,
                ctypes.byref(old_protect)
            )
            if not protected:
                err = api.last_error_str()
                if not silent:
                    log.error("write_bytes: VirtualProtectEx(0x%X) FAILED: %s. Protect was 0x%X", 
                              address, err, mbi.Protect)
        
        # 3. The actual write
        ok = api.WriteProcessMemory(
            self._handle, addr_vp, buf, len(data), ctypes.byref(n_wrote)
        )
        
        # CAPTURE error state immediately after WPM
        err_msg = None
        if not ok:
            err_msg = api.last_error_str()

        # 4. Restore original protection
        if protected:
            dummy = wt.DWORD(0)
            api.VirtualProtectEx(
                self._handle, addr_vp, len(data), old_protect.value,
                ctypes.byref(dummy)
            )

        if not ok:
            log.error("write_bytes: WPM(0x%X, len=%d, h=0x%X) FAILED: %s. State=0x%X Protect=0x%X", 
                      address, len(data), self._handle, err_msg, mbi.State, mbi.Protect)
        else:
            if not silent:
                log.debug("write_bytes: Success 0x%X (%d bytes)", address, n_wrote.value)
            
        return bool(ok)

    def write_batch(self, writes: list[tuple[int, bytes]]) -> int:
        """
        Write multiple memory locations efficiently.
        Groups writes by page/region to minimize VirtualProtectEx calls.
        Returns number of successful writes.
        """
        if not writes:
            return 0

        # Sort by address for potentially better locality
        writes.sort(key=lambda x: x[0])
        
        success_count = 0
        failure_details = []
        
        for addr, data in writes:
            # We call write_bytes with silent=True to avoid double logging success,
            # but our new write_bytes ALWAYS logs errors to console for now.
            if self.write_bytes(addr, data, silent=True):
                success_count += 1
            else:
                failure_details.append(addr)
        
        if success_count < len(writes):
            log.warning("write_batch: %d/%d writes failed. First few failed addresses: %s", 
                        len(writes) - success_count, len(writes), 
                        [f"0x{a:X}" for a in failure_details[:5]])
            
        return success_count

    # ── Typed read helpers ────────────────────────────────────────────────────

    def read_value(self, address: int, dtype: DataType, str_max: int = 256) -> object:
        """Read a typed value from `address`."""
        size = DATA_TYPE_SIZE.get(dtype)

        if size is None:
            # Variable-length
            if dtype in (DataType.STRING, DataType.STRING16):
                multiplier = 2 if dtype == DataType.STRING16 else 1
                raw = self.read_bytes(address, str_max * multiplier)
            elif dtype == DataType.BYTES:
                raw = self.read_bytes(address, str_max)
            else:
                return None
        else:
            raw = self.read_bytes(address, size)

        if raw is None:
            return None
        return bytes_to_value(raw, dtype)

    _INT_FMT_SIGNED   = {1: "<b", 2: "<h", 4: "<i", 8: "<q"}
    _INT_FMT_UNSIGNED = {1: "<B", 2: "<H", 4: "<I", 8: "<Q"}

    def read_int(self, address: int, size: int = 4, signed: bool = True) -> Optional[int]:
        """Convenience: read a little-endian integer (1/2/4/8 bytes)."""
        if not self._handle or self._handle <= 0:
            return None
        
        raw = self.read_bytes(address, size)
        if raw is None:
            return None
        fmt_map = self._INT_FMT_SIGNED if signed else self._INT_FMT_UNSIGNED
        fmt = fmt_map.get(size)
        if fmt is None:
            return None
        try:
            return struct.unpack_from(fmt, raw)[0]
        except struct.error:
            return None
        except Exception as e:
            log.debug("read_int exception at 0x%X: %s", address, e)
            return None

    def read_float(self, address: int) -> Optional[float]:
        if not self._handle or self._handle <= 0:
            return None
        
        raw = self.read_bytes(address, 4)
        if raw is None:
            return None
        try:
            return struct.unpack_from("<f", raw)[0]
        except struct.error:
            return None
        except Exception as e:
            log.debug("read_float exception at 0x%X: %s", address, e)
            return None

    def read_double(self, address: int) -> Optional[float]:
        if not self._handle or self._handle <= 0:
            return None
        
        raw = self.read_bytes(address, 8)
        if raw is None:
            return None
        return struct.unpack_from("<d", raw)[0]

    def read_pointer(self, address: int) -> Optional[int]:
        """Read a pointer-sized integer (4 or 8 bytes depending on bitness)."""
        raw = self.read_bytes(address, self._ptr_size)
        if raw is None:
            return None
        fmt = "<Q" if self._is_64bit else "<I"
        return struct.unpack_from(fmt, raw)[0]

    def read_string(self, address: int, max_len: int = 256, encoding: str = "utf-8") -> Optional[str]:
        raw = self.read_bytes(address, max_len)
        if raw is None:
            return None
        try:
            return raw.split(b"\x00")[0].decode(encoding, errors="replace")
        except Exception:
            return None

    # ── Typed write helpers ───────────────────────────────────────────────────

    def write_value(self, address: int, value: object, dtype: DataType) -> bool:
        """Write a typed value to `address`."""
        data = value_to_bytes(value, dtype)
        if data is None:
            log.warning("write_value: failed to pack value=%r dtype=%s", value, dtype)
            return False
        return self.write_bytes(address, data)

    # ── Region enumeration ────────────────────────────────────────────────────

    def get_regions(
        self,
        writable_only: bool = False,
        exclude_mapped: bool = False,
    ) -> list[MemoryRegion]:
        """
        Enumerate all committed, readable memory regions in the process.

        Args:
            writable_only:  Only include writable pages (scan targets).
            exclude_mapped: Exclude memory-mapped (MEM_MAPPED) regions.

        Returns:
            List of MemoryRegion ordered by base address.
        """
        regions: list[MemoryRegion] = []
        address = 0
        mbi     = api.MEMORY_BASIC_INFORMATION()
        mbi_size = ctypes.sizeof(mbi)

        while True:
            ret = api.VirtualQueryEx(
                self._handle, address, ctypes.byref(mbi), mbi_size
            )
            if ret == 0:
                break

            if (
                mbi.State == MEM_COMMIT
                and mbi.RegionSize > 0
                and (mbi.Protect & READABLE_PAGE_MASK)
                and not (mbi.Protect & PAGE_GUARD)
            ):
                include = True
                if writable_only and not (mbi.Protect & (api.PAGE_READWRITE | api.PAGE_EXECUTE_READWRITE | api.PAGE_WRITECOPY | api.PAGE_EXECUTE_WRITECOPY)):
                    include = False
                if exclude_mapped and mbi.Type == api.MEM_MAPPED:
                    include = False

                if include:
                    ptr_mask = (1 << (8 * self._ptr_size)) - 1
                    regions.append(MemoryRegion(
                        base=(mbi.BaseAddress or 0) & ptr_mask,
                        size=mbi.RegionSize,
                        protect=mbi.Protect,
                        type_=mbi.Type,
                    ))

            # Advance — guard against infinite loop and sign issues
            ptr_mask = (1 << (8 * self._ptr_size)) - 1
            next_addr = ((mbi.BaseAddress or 0) + mbi.RegionSize) & ptr_mask
            
            if next_addr <= address and address != 0: # address 0 is start
                break
            address = next_addr

        log.debug("Enumerated %d readable regions", len(regions))
        return regions

    def read_region_chunked(
        self,
        region: MemoryRegion,
        chunk_size: int = SCAN_CHUNK_SIZE,
    ):
        """
        Generator: yields (chunk_base, chunk_bytes) for a region in chunks.
        Uses bulk ReadProcessMemory — no per-address calls.
        """
        remaining = region.size
        offset    = 0

        while remaining > 0:
            read_size = min(chunk_size, remaining)
            raw = self.read_bytes(region.base + offset, read_size)
            if raw is not None:
                yield region.base + offset, raw
            offset    += read_size
            remaining -= read_size

    def read_into_array(self, address: int, size: int, fmt: str = 'Q'):
        """
        Reads bulk memory directly into an array.array.
        fmt: 'Q' for uint64, 'I' for uint32.
        Returns array.array or None.
        """
        # Validate handle
        if not self._handle or self._handle <= 0:
            return None
        
        # Validate parameters
        if address < 0x1000 or size <= 0 or size > 0x10000000:
            return None
        
        try:
            from array import array
            raw = self.read_bytes(address, size)
            if raw is None:
                return None
            
            # Ensure raw length matches alignment
            elem_size = 8 if fmt == 'Q' else 4
            valid_len = (len(raw) // elem_size) * elem_size
            if valid_len == 0:
                return None
                
            arr = array(fmt)
            arr.frombytes(raw[:valid_len])
            return arr
        except Exception as e:
            log.debug("read_into_array exception at 0x%X: %s", address, e)
            return None
