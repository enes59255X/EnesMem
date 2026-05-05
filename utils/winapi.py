"""
winapi.py — Pure ctypes WinAPI declarations.
Single source of truth: ALL Windows API calls go through here.
Supports both 32-bit and 64-bit target processes.
No pymem or pywin32 dependency.
"""
import ctypes
import ctypes.wintypes as wt
from ctypes import windll, POINTER, c_void_p, c_size_t, c_char, c_ulong

# ─── Handle constants ─────────────────────────────────────────────────────────
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

# ─── Process access rights ────────────────────────────────────────────────────
PROCESS_QUERY_INFORMATION   = 0x0400
PROCESS_QUERY_LIMITED_INFO  = 0x1000
PROCESS_VM_READ             = 0x0010
PROCESS_VM_WRITE            = 0x0020
PROCESS_VM_OPERATION        = 0x0008
PROCESS_ALL_ACCESS          = 0x1F0FFF

# ─── Memory state / type ─────────────────────────────────────────────────────
MEM_COMMIT  = 0x00001000
MEM_RESERVE = 0x00002000
MEM_FREE    = 0x00010000
MEM_PRIVATE = 0x00020000
MEM_MAPPED  = 0x00040000
MEM_IMAGE   = 0x01000000

# ─── Memory protection ───────────────────────────────────────────────────────
PAGE_NOACCESS          = 0x01
PAGE_READONLY          = 0x02
PAGE_READWRITE         = 0x04
PAGE_WRITECOPY         = 0x08
PAGE_EXECUTE           = 0x10
PAGE_EXECUTE_READ      = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_WRITECOPY = 0x80
PAGE_GUARD             = 0x100
PAGE_NOCACHE           = 0x200
PAGE_WRITECOMBINE      = 0x400

# Pages that are readable (mask for Protect field)
READABLE_PAGE_MASK = (
    PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
    PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
)

# ─── Snapshot flags ──────────────────────────────────────────────────────────
TH32CS_SNAPPROCESS  = 0x00000002
TH32CS_SNAPMODULE   = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010


# ─── Structures ───────────────────────────────────────────────────────────────

class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    """VirtualQueryEx result — describes a contiguous region of virtual memory."""
    _fields_ = [
        ("BaseAddress",       c_void_p),
        ("AllocationBase",    c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("__alignment1",      wt.DWORD),   # Alignment for RegionSize
        ("RegionSize",        c_size_t),
        ("State",             wt.DWORD),
        ("Protect",           wt.DWORD),
        ("Type",              wt.DWORD),
        ("__alignment2",      wt.DWORD),   # Pad to 48 bytes on x64
    ]


class PROCESSENTRY32(ctypes.Structure):
    """Entry in a process snapshot."""
    _fields_ = [
        ("dwSize",              wt.DWORD),
        ("cntUsage",            wt.DWORD),
        ("th32ProcessID",       wt.DWORD),
        ("th32DefaultHeapID",   c_size_t),   # ULONG_PTR — pointer-sized
        ("th32ModuleID",        wt.DWORD),
        ("cntThreads",          wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase",      ctypes.c_long),
        ("dwFlags",             wt.DWORD),
        ("szExeFile",           c_char * 260),
    ]


class MODULEENTRY32(ctypes.Structure):
    """Entry in a module snapshot."""
    _fields_ = [
        ("dwSize",        wt.DWORD),
        ("th32ModuleID",  wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("GlblcntUsage",  wt.DWORD),
        ("ProccntUsage",  wt.DWORD),
        ("modBaseAddr",   POINTER(wt.BYTE)),
        ("modBaseSize",   wt.DWORD),
        ("hModule",       wt.HMODULE),
        ("szModule",      c_char * 256),
        ("szExePath",     c_char * 260),
    ]


# ─── Kernel32 handle ─────────────────────────────────────────────────────────
_k32 = windll.kernel32


# ─── Process management ──────────────────────────────────────────────────────

OpenProcess = _k32.OpenProcess
OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
OpenProcess.restype  = wt.HANDLE

CloseHandle = _k32.CloseHandle
CloseHandle.argtypes = [wt.HANDLE]
CloseHandle.restype  = wt.BOOL

IsWow64Process = _k32.IsWow64Process
IsWow64Process.argtypes = [wt.HANDLE, POINTER(wt.BOOL)]
IsWow64Process.restype  = wt.BOOL

GetLastError = _k32.GetLastError
GetLastError.argtypes = []
GetLastError.restype  = wt.DWORD

# ─── Memory operations ───────────────────────────────────────────────────────

ReadProcessMemory = _k32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    wt.HANDLE, c_void_p, c_void_p, c_size_t, POINTER(c_size_t)
]
ReadProcessMemory.restype = wt.BOOL

WriteProcessMemory = _k32.WriteProcessMemory
WriteProcessMemory.argtypes = [
    wt.HANDLE, c_void_p, c_void_p, c_size_t, POINTER(c_size_t)
]
WriteProcessMemory.restype = wt.BOOL

VirtualQueryEx = _k32.VirtualQueryEx
VirtualQueryEx.argtypes = [
    wt.HANDLE, c_void_p, POINTER(MEMORY_BASIC_INFORMATION), c_size_t
]
VirtualQueryEx.restype = c_size_t

VirtualProtectEx = _k32.VirtualProtectEx
VirtualProtectEx.argtypes = [
    wt.HANDLE, c_void_p, c_size_t, wt.DWORD, POINTER(wt.DWORD)
]
VirtualProtectEx.restype = wt.BOOL

# ─── Snapshot / enumeration ──────────────────────────────────────────────────

CreateToolhelp32Snapshot = _k32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
CreateToolhelp32Snapshot.restype  = wt.HANDLE

Process32First = _k32.Process32First
Process32First.argtypes = [wt.HANDLE, POINTER(PROCESSENTRY32)]
Process32First.restype  = wt.BOOL

Process32Next = _k32.Process32Next
Process32Next.argtypes = [wt.HANDLE, POINTER(PROCESSENTRY32)]
Process32Next.restype  = wt.BOOL

Module32First = _k32.Module32First
Module32First.argtypes = [wt.HANDLE, POINTER(MODULEENTRY32)]
Module32First.restype  = wt.BOOL

Module32Next = _k32.Module32Next
Module32Next.argtypes = [wt.HANDLE, POINTER(MODULEENTRY32)]
Module32Next.restype  = wt.BOOL


# ─── Helper: get last error string ───────────────────────────────────────────

def last_error_str() -> str:
    """Return a human-readable string for the last WinAPI error."""
    code = GetLastError()
    try:
        msg = ctypes.FormatError(code)
    except Exception:
        msg = f"Unknown error"
    return f"[WinError {code}] {msg}"
