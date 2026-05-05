"""
patterns.py — Enums and constants used across all modules.
Single source of truth for scan modes, data types, and sizing.
"""
from enum import Enum
import struct


class DataType(Enum):
    INT8     = "1-byte Integer"
    INT16    = "2-byte Integer"
    INT32    = "4-byte Integer"
    INT64    = "8-byte Integer"
    FLOAT    = "Float"
    DOUBLE   = "Double"
    STRING   = "String (UTF-8)"
    STRING16 = "String (UTF-16LE)"
    BYTES    = "Byte Array (AOB)"


class ScanMode(Enum):
    EXACT           = "Exact Value"
    BIGGER          = "Bigger Than"
    SMALLER         = "Smaller Than"
    BETWEEN         = "Between (A and B)"
    INCREASED       = "Increased Value"
    DECREASED       = "Decreased Value"
    INCREASED_BY    = "Increased Value By"
    DECREASED_BY    = "Decreased Value By"
    CHANGED         = "Changed Value"
    UNCHANGED       = "Unchanged Value"
    UNKNOWN         = "Unknown Initial Value"
    FLOAT_TOLERANCE = "Float Tolerance (±)"
    AOB             = "Array of Bytes (Wildcard)"


# Data type → byte size (None = variable-length)
DATA_TYPE_SIZE: dict[DataType, int | None] = {
    DataType.INT8:     1,
    DataType.INT16:    2,
    DataType.INT32:    4,
    DataType.INT64:    8,
    DataType.FLOAT:    4,
    DataType.DOUBLE:   8,
    DataType.STRING:   None,
    DataType.STRING16: None,
    DataType.BYTES:    None,
}

# Data type → struct format string
DATA_TYPE_STRUCT: dict[DataType, str] = {
    DataType.INT8:   "<b",
    DataType.INT16:  "<h",
    DataType.INT32:  "<i",
    DataType.INT64:  "<q",
    DataType.FLOAT:  "<f",
    DataType.DOUBLE: "<d",
}

# Scan modes that need a previous snapshot (two values to compare)
RELATIVE_SCAN_MODES = {
    ScanMode.INCREASED,
    ScanMode.DECREASED,
    ScanMode.INCREASED_BY,
    ScanMode.DECREASED_BY,
    ScanMode.CHANGED,
    ScanMode.UNCHANGED,
}

# Scan modes that require a single numeric value input
VALUE_INPUT_MODES = {
    ScanMode.EXACT,
    ScanMode.BIGGER,
    ScanMode.SMALLER,
    ScanMode.INCREASED_BY,
    ScanMode.DECREASED_BY,
    ScanMode.FLOAT_TOLERANCE,
    ScanMode.AOB,
}

# Scan modes that take a range (two values: low and high)
RANGE_INPUT_MODES = {
    ScanMode.BETWEEN,
}

# Numeric data types (support comparison operators)
NUMERIC_TYPES = {
    DataType.INT8,
    DataType.INT16,
    DataType.INT32,
    DataType.INT64,
    DataType.FLOAT,
    DataType.DOUBLE,
}

# Float/double types (support tolerance comparison)
FLOAT_TYPES = {
    DataType.FLOAT,
    DataType.DOUBLE,
}

# WinAPI memory access permission flags
PROCESS_ALL_ACCESS    = 0x1F0FFF
MEM_COMMIT            = 0x1000
PAGE_NOACCESS         = 0x01
PAGE_READABLE         = (
    0x02 | 0x04 | 0x08 | 0x20 | 0x40 | 0x80
)  # READONLY | READWRITE | WRITECOPY | EXECUTE_READ | EXECUTE_READWRITE | EXECUTE_WRITECOPY
PAGE_GUARD            = 0x100

# Max chunk size for bulk memory reads (4 MB)
SCAN_CHUNK_SIZE = 4 * 1024 * 1024

# Live refresh interval for results table (ms)
LIVE_REFRESH_INTERVAL_MS = 500

# Freeze write interval (seconds)
FREEZE_INTERVAL_SEC = 0.05

# Export/import constants
EXPORT_MAX_RESULTS = 50_000
