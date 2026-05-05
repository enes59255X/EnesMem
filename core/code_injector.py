"""
code_injector.py — Low-level code injection utilities.
WARNING: For educational and authorized use ONLY.
Incorrect use will crash the target process.
"""
import ctypes
import struct
from typing import Optional

from utils import winapi as api
from utils.logger import log

# Win32 constants
MEM_COMMIT             = 0x1000
MEM_RESERVE            = 0x2000
MEM_RELEASE            = 0x8000
PAGE_READWRITE         = 0x04
PAGE_EXECUTE_READWRITE = 0x40
VIRTUAL_MEM            = MEM_COMMIT | MEM_RESERVE


class CodeInjector:
    """
    Write-level code patching for an open process handle.
    All methods require PAGE_EXECUTE_READWRITE on target pages
    (call make_executable first, or it will be called automatically).
    """

    def __init__(self, handle: int, is_64bit: bool = True) -> None:
        self._handle  = handle
        self._is64    = is_64bit
        self._backups: dict[int, bytes] = {}  # address → original bytes

    # ── Low-level byte I/O ────────────────────────────────────────────────────

    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        buf    = (ctypes.c_char * size)()
        n_read = ctypes.c_size_t(0)
        ok = api.ReadProcessMemory(
            self._handle, address, buf, size, ctypes.byref(n_read)
        )
        return bytes(buf) if ok and n_read.value == size else None

    def write_bytes(self, address: int, data: bytes) -> bool:
        buf     = (ctypes.c_char * len(data))(*data)
        n_wrote = ctypes.c_size_t(0)
        ok = api.WriteProcessMemory(
            self._handle, address, buf, len(data), ctypes.byref(n_wrote)
        )
        if not ok:
            log.warning("write_bytes(0x%X) failed: %s", address, api.last_error_str())
        return bool(ok)

    # ── Page protection ───────────────────────────────────────────────────────

    def make_executable(self, address: int, size: int) -> tuple[bool, int]:
        """
        Set PAGE_EXECUTE_READWRITE on the target pages.
        Returns (success, old_protection_value).
        """
        kernel32  = ctypes.windll.kernel32
        old_prot  = ctypes.c_ulong(0)
        ok = kernel32.VirtualProtectEx(
            ctypes.c_void_p(self._handle),
            ctypes.c_void_p(address),
            ctypes.c_size_t(size),
            PAGE_EXECUTE_READWRITE,
            ctypes.byref(old_prot),
        )
        if not ok:
            log.warning("VirtualProtectEx(0x%X) failed: %d", address, ctypes.get_last_error())
        return bool(ok), old_prot.value

    def restore_protection(self, address: int, size: int, old_protect: int) -> bool:
        kernel32 = ctypes.windll.kernel32
        dummy    = ctypes.c_ulong(0)
        return bool(kernel32.VirtualProtectEx(
            ctypes.c_void_p(self._handle),
            ctypes.c_void_p(address),
            ctypes.c_size_t(size),
            old_protect,
            ctypes.byref(dummy),
        ))

    # ── NOP sled ─────────────────────────────────────────────────────────────

    def nop_sled(self, address: int, size: int, backup: bool = True) -> bool:
        """Overwrite `size` bytes with 0x90 (NOP). Saves backup if requested."""
        if backup:
            orig = self.read_bytes(address, size)
            if orig:
                self._backups[address] = orig

        ok_p, old = self.make_executable(address, size)
        result    = self.write_bytes(address, b'\x90' * size)
        if ok_p:
            self.restore_protection(address, size, old)

        log.info("NOP sled: 0x%X  size=%d  ok=%s", address, size, result)
        return result

    # ── JMP hook ─────────────────────────────────────────────────────────────

    def write_jmp(self, from_addr: int, to_addr: int, backup: bool = True) -> bool:
        """
        Write a JMP instruction at from_addr targeting to_addr.
        - Near (±2 GB): E9 <rel32>  — 5 bytes
        - Far  (64-bit): FF 25 00000000 <abs64> — 14 bytes
        """
        rel      = to_addr - from_addr - 5
        use_far  = self._is64 and not (-2**31 <= rel <= 2**31 - 1)
        jmp_size = 14 if use_far else 5

        if backup:
            orig = self.read_bytes(from_addr, jmp_size)
            if orig:
                self._backups[from_addr] = orig

        ok_p, old = self.make_executable(from_addr, jmp_size)

        if use_far:
            patch = b'\xFF\x25\x00\x00\x00\x00' + struct.pack('<Q', to_addr)
        else:
            patch = b'\xE9' + struct.pack('<i', rel)

        result = self.write_bytes(from_addr, patch)
        if ok_p:
            self.restore_protection(from_addr, jmp_size, old)

        log.info("JMP 0x%X → 0x%X  far=%s  ok=%s", from_addr, to_addr, use_far, result)
        return result

    # ── Patch arbitrary bytes ─────────────────────────────────────────────────

    def patch_bytes(self, address: int, data: bytes, backup: bool = True) -> bool:
        """Write arbitrary bytes, making page executable first."""
        if backup:
            orig = self.read_bytes(address, len(data))
            if orig:
                self._backups[address] = orig

        ok_p, old = self.make_executable(address, len(data))
        result    = self.write_bytes(address, data)
        if ok_p:
            self.restore_protection(address, len(data), old)
        return result

    # ── DLL injection ─────────────────────────────────────────────────────────

    def inject_dll(self, dll_path: str) -> bool:
        """
        Classic CreateRemoteThread + LoadLibraryA injection.
        Same-architecture only (64-bit EnesMem → 64-bit target).
        """
        kernel32   = ctypes.windll.kernel32
        path_bytes = dll_path.encode('utf-8') + b'\x00'
        path_len   = len(path_bytes)

        # Allocate memory in target process for DLL path
        remote_mem = kernel32.VirtualAllocEx(
            ctypes.c_void_p(self._handle),
            None,
            ctypes.c_size_t(path_len),
            VIRTUAL_MEM,
            PAGE_READWRITE,
        )
        if not remote_mem:
            log.error("VirtualAllocEx failed for DLL injection")
            return False

        # Write DLL path string
        buf     = (ctypes.c_char * path_len)(*path_bytes)
        n_wrote = ctypes.c_size_t(0)
        ok = api.WriteProcessMemory(
            self._handle, remote_mem, buf, path_len, ctypes.byref(n_wrote)
        )
        if not ok:
            kernel32.VirtualFreeEx(
                ctypes.c_void_p(self._handle),
                ctypes.c_void_p(remote_mem), 0, MEM_RELEASE,
            )
            log.error("WriteProcessMemory for DLL path failed")
            return False

        # Resolve LoadLibraryA address
        k32_handle  = kernel32.GetModuleHandleA(b'kernel32.dll')
        load_lib    = kernel32.GetProcAddress(k32_handle, b'LoadLibraryA')
        if not load_lib:
            log.error("GetProcAddress(LoadLibraryA) failed")
            return False

        # Spawn remote thread
        thread_id = ctypes.c_ulong(0)
        h_thread  = kernel32.CreateRemoteThread(
            ctypes.c_void_p(self._handle),
            None, 0,
            ctypes.c_void_p(load_lib),
            ctypes.c_void_p(remote_mem),
            0,
            ctypes.byref(thread_id),
        )
        if not h_thread:
            log.error("CreateRemoteThread failed: %d", ctypes.get_last_error())
            return False

        kernel32.WaitForSingleObject(ctypes.c_void_p(h_thread), 5000)
        kernel32.CloseHandle(ctypes.c_void_p(h_thread))
        kernel32.VirtualFreeEx(
            ctypes.c_void_p(self._handle),
            ctypes.c_void_p(remote_mem), 0, MEM_RELEASE,
        )

        log.info("DLL injected: %s", dll_path)
        return True

    # ── Restore ───────────────────────────────────────────────────────────────

    def restore(self, address: int) -> bool:
        """Restore original bytes from backup at address."""
        orig = self._backups.pop(address, None)
        if orig is None:
            log.warning("No backup for 0x%X", address)
            return False
        ok_p, old = self.make_executable(address, len(orig))
        result    = self.write_bytes(address, orig)
        if ok_p:
            self.restore_protection(address, len(orig), old)
        log.info("Restored 0x%X (%d bytes)", address, len(orig))
        return result

    def restore_all(self) -> int:
        """Restore all backed-up patches. Returns count of successful restores."""
        return sum(1 for addr in list(self._backups) if self.restore(addr))

    @property
    def patch_count(self) -> int:
        return len(self._backups)
