"""
process_manager.py — Process enumeration, handle management, module listing.
All Windows process operations go through this class.
"""
import ctypes
import ctypes.wintypes as wt
from dataclasses import dataclass, field
from typing import Optional

from utils import winapi as api
from utils.logger import log


@dataclass
class ProcessInfo:
    pid:        int
    name:       str
    parent_pid: int
    threads:    int

    def __str__(self) -> str:
        return f"{self.name} (PID: {self.pid})"


@dataclass
class ModuleInfo:
    name:      str
    base_addr: int
    size:      int
    path:      str

    def __str__(self) -> str:
        return f"{self.name} @ 0x{self.base_addr:X} (size={self.size:#x})"


class ProcessManager:
    """
    Manages a single open process handle.
    Thread-safe: handle is opened/closed explicitly, not on GC.
    """

    def __init__(self) -> None:
        self._handle:  Optional[int] = None
        self._pid:     int = 0
        self._name:    str = ""
        self._is_64bit: bool = True

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def handle(self) -> Optional[int]:
        return self._handle

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_64bit(self) -> bool:
        return self._is_64bit

    @property
    def is_attached(self) -> bool:
        return self._handle is not None

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def list_processes() -> list[ProcessInfo]:
        """Return a sorted list of all running processes."""
        results: list[ProcessInfo] = []
        snap = api.CreateToolhelp32Snapshot(api.TH32CS_SNAPPROCESS, 0)

        if snap == api.INVALID_HANDLE_VALUE:
            log.error("CreateToolhelp32Snapshot failed: %s", api.last_error_str())
            return results

        entry = api.PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(api.PROCESSENTRY32)

        try:
            if api.Process32First(snap, ctypes.byref(entry)):
                while True:
                    results.append(ProcessInfo(
                        pid=entry.th32ProcessID,
                        name=entry.szExeFile.decode("utf-8", errors="replace"),
                        parent_pid=entry.th32ParentProcessID,
                        threads=entry.cntThreads,
                    ))
                    if not api.Process32Next(snap, ctypes.byref(entry)):
                        break
        finally:
            api.CloseHandle(snap)

        return sorted(results, key=lambda p: p.name.lower())

    @staticmethod
    def find_pid(process_name: str) -> Optional[int]:
        """Find the first PID matching process_name (case-insensitive)."""
        name_lower = process_name.lower()
        for proc in ProcessManager.list_processes():
            if proc.name.lower() == name_lower:
                return proc.pid
        return None

    # ── Handle lifecycle ──────────────────────────────────────────────────────

    def open_process(self, pid: int) -> bool:
        """
        Open a handle to the given PID with PROCESS_ALL_ACCESS.
        Returns True on success. Closes any previously open handle.
        """
        self.close_handle()

        handle = api.OpenProcess(api.PROCESS_ALL_ACCESS, False, pid)
        if not handle:
            log.error("OpenProcess(%d) failed: %s", pid, api.last_error_str())
            return False

        self._handle   = handle
        self._pid      = pid
        self._is_64bit = self._detect_64bit(handle)

        # Resolve process name
        for proc in ProcessManager.list_processes():
            if proc.pid == pid:
                self._name = proc.name
                break
        else:
            self._name = f"PID:{pid}"

        log.info(
            "Attached to %s (PID=%d, 64-bit=%s)",
            self._name, self._pid, self._is_64bit
        )
        return True

    def close_handle(self) -> None:
        """Close the current process handle if open."""
        if self._handle:
            api.CloseHandle(self._handle)
            log.info("Detached from %s (PID=%d)", self._name, self._pid)
            self._handle  = None
            self._pid     = 0
            self._name    = ""

    # ── Module enumeration ────────────────────────────────────────────────────

    def get_modules(self) -> list[ModuleInfo]:
        """
        Return all loaded modules in the attached process.
        Uses TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32 to catch both 32-bit
        and 64-bit modules in WOW64 processes.
        """
        if not self._handle:
            return []

        flags = api.TH32CS_SNAPMODULE | api.TH32CS_SNAPMODULE32
        snap  = api.CreateToolhelp32Snapshot(flags, self._pid)
        if snap == api.INVALID_HANDLE_VALUE:
            log.error("Module snapshot failed: %s", api.last_error_str())
            return []

        results: list[ModuleInfo] = []
        entry = api.MODULEENTRY32()
        entry.dwSize = ctypes.sizeof(api.MODULEENTRY32)

        try:
            if api.Module32First(snap, ctypes.byref(entry)):
                while True:
                    base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value or 0
                    results.append(ModuleInfo(
                        name=entry.szModule.decode("utf-8", errors="replace"),
                        base_addr=base,
                        size=entry.modBaseSize,
                        path=entry.szExePath.decode("utf-8", errors="replace"),
                    ))
                    if not api.Module32Next(snap, ctypes.byref(entry)):
                        break
        finally:
            api.CloseHandle(snap)

        return results

    def find_module(self, name: str) -> Optional[ModuleInfo]:
        """Find a module by name (case-insensitive)."""
        name_lower = name.lower()
        for mod in self.get_modules():
            if mod.name.lower() == name_lower:
                return mod
        return None

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _detect_64bit(handle: int) -> bool:
        """
        Detect whether the target process is 64-bit.
        IsWow64Process returns True if a 64-bit OS is running a 32-bit process.
        """
        is_wow64 = wt.BOOL(False)
        if api.IsWow64Process(handle, ctypes.byref(is_wow64)):
            # Running on 64-bit OS: if WOW64 → 32-bit process
            return not bool(is_wow64.value)
        # If the call fails, assume native
        return True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close_handle()

    def __repr__(self) -> str:
        return f"ProcessManager(pid={self._pid}, name={self._name!r}, attached={self.is_attached})"
